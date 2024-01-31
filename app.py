import enum
import json
import os
import re
from typing import Any, List, Mapping, Optional

import openai
import streamlit as st
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.callbacks import FileCallbackHandler
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, StreamlitChatMessageHistory
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder, \
    PromptTemplate, SystemMessagePromptTemplate
from langchain_core.tools import BaseTool
from llama_hub.tools.waii import WaiiToolSpec
from llama_index.tools import FunctionTool
from llmonitor.langchain import LLMonitorCallbackHandler
from requests import RequestException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

from create import create_snowflake_transformation, get_transformation_url
from prompts import ai_intro, custom_gen_sql, kai_gen_sql

_ST_CHAT_HiSTORY_KEY = 'sql-bot-message-history-in-streamlit'
_ST_TRANS_QUERY = 'transformation_query'
_ST_TRANS_DETAILS = 'transformation_details'


class _Model(enum.Enum):
    GPT_4_TURBO = 'gpt-4-1106-preview'
    GPT_4 = 'gpt-4'
    GPT_35_TURBO = 'gpt-3.5-turbo-16k'

    @staticmethod
    def from_text(text: str) -> Optional['_Model']:
        for m in _Model:
            if m.value == text:
                return m


class _Toolkit(enum.Enum):
    WAII = 'WAII Tools'
    LANGCHAIN = 'Langchain SQL Tools'

    @staticmethod
    def from_text(text: str) -> Optional['_Toolkit']:
        for m in _Toolkit:
            if m.value == text:
                return m


def _get_waii_tools() -> List[BaseTool]:
    conn_string = (f'snowflake://{st.secrets["user"]}@{st.secrets["account_identifier"]}/{st.secrets["database_name"]}'
                   f'?role={st.secrets["user"]}&warehouse={st.secrets["warehouse_name"]}')
    waii_api_key = st.secrets['waii_prod_api_key']
    waii_tool_spec = WaiiToolSpec(
        url='https://tweakit.waii.ai/api/',
        api_key=waii_api_key,
        database_key=conn_string,
        verbose=True
    )
    waii_tools: List[FunctionTool] = waii_tool_spec.to_tool_list()
    langchain_tools = [t.to_langchain_tool() for t in waii_tools]

    waii_tools_descriptions = [(t.metadata.name, t.metadata.description) for t in waii_tools]
    langchain_tools_descriptions = [(t.name, t.description) for t in langchain_tools]
    assert waii_tools_descriptions == langchain_tools_descriptions

    return langchain_tools


def _get_langchain_tools(llm: BaseLanguageModel) -> List[BaseTool]:
    conn_string = (f'snowflake://{st.secrets["user"]}:{st.secrets["password"]}'
                   f'@{st.secrets["account_identifier"]}/{st.secrets["database_name"]}/{st.secrets["schema_name"]}'
                   f'?role={st.secrets["user"]}&warehouse={st.secrets["warehouse_name"]}')
    return SQLDatabaseToolkit(db=SQLDatabase.from_uri(conn_string), llm=llm).get_tools()


def _create_agent(model: _Model, toolkit: _Toolkit) -> AgentExecutor:
    llm = ChatOpenAI(model=model.value, temperature=0, streaming=True)
    if toolkit == _Toolkit.WAII:
        tools = _get_waii_tools()
        system_prompt = SystemMessagePromptTemplate(prompt=kai_gen_sql)
    elif toolkit == _Toolkit.LANGCHAIN:
        tools = _get_langchain_tools(llm)
        system_prompt = SystemMessagePromptTemplate(prompt=custom_gen_sql)
    else:
        raise ValueError(f'Unknown toolkit: {toolkit}')

    prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
        system_prompt,
        MessagesPlaceholder(variable_name='chat_history'),
        HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['input'], template='{input}')),
        MessagesPlaceholder(variable_name='agent_scratchpad')
    ])
    chat_memory = StreamlitChatMessageHistory(key=_ST_CHAT_HiSTORY_KEY)
    chat_memory.clear()

    return AgentExecutor(
        agent=create_openai_tools_agent(llm, tools, prompt=prompt),
        tools=tools,
        verbose=True,
        memory=ConversationBufferMemory(memory_key='chat_history', chat_memory=chat_memory, return_messages=True)
    )


def _call_agent(agent: AgentExecutor, user_input: str) -> Mapping[str, Any]:
    return agent.invoke(
        input={'input': user_input},
        config={'callbacks': [
            StreamlitCallbackHandler(st.container(), expand_new_thoughts=True),
            LLMonitorCallbackHandler(app_id=st.secrets.LUNARY_APP_ID),
            FileCallbackHandler('chat_log.txt'),
        ]}
    )


class _AIConfig(BaseModel):
    ai_tr_name: str = Field(description='name of the transformation (with spaces between words)')
    ai_tr_description: str = Field(description='description of the transformation')
    ai_output_table: str = Field(description='name of the output table')


def _generate_config_details(chat_history: List[BaseMessage], model: _Model) -> Mapping[str, Any]:
    model = ChatOpenAI(model=model.value, temperature=0)
    ai_query = f'''
Based on the conversation history between Human and AI, create a SQL transformation name (max 8 words), 
description (max 500 characters) and output table name adhering to Snowflake naming conventions. Focus on describing the user's business intent. 
        {chat_history}'''

    parser = JsonOutputParser(pydantic_object=_AIConfig)
    
    prompt = PromptTemplate(
        template='Answer the user query.\n{format_instructions}\n{query}\n',
        input_variables=['query'],
        partial_variables={'format_instructions': parser.get_format_instructions()},
    )
    chain = prompt | model | parser

    return chain.invoke({'query': ai_query})


def app():
    openai.api_key = st.secrets.OPENAI_API_KEY

    image_path = os.path.dirname(os.path.abspath(__file__))
    st.image(image_path+'/static/keboola_logo.png', width=200)
    home_title = 'Kai SQL Bot'  # Replace with your title
    st.markdown(f'# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>', unsafe_allow_html=True)

    st.sidebar.markdown(f'## {home_title} Settings')
    model_current = _Model.from_text(st.sidebar.selectbox(
        label='Choose a model',
        options=[m.value for m in _Model],
        help='Select the model you want to use for the chatbot.'
    ))
    model_last = _Model.from_text(st.session_state.get('model'))
    toolkit_current = _Toolkit.from_text(st.sidebar.selectbox(
        label='Choose tools',
        options=[t.value for t in _Toolkit],
        help='Select the tools you want to use for the chatbot.'
    ))
    toolkit_last = _Toolkit.from_text(st.session_state.get('toolkit'))

    if model_last != model_current or toolkit_last != toolkit_current:
        # reset the agent
        agent = _create_agent(model_current, toolkit_current)
        st.session_state['agent'] = agent
        # store string to the session, using custom classes results in different type instances create after each
        # streamlit re-run and comparing the seemingly same class instances does not work then
        st.session_state['model'] = model_current.value
        st.session_state['toolkit'] = toolkit_current.value
    else:
        agent = st.session_state.agent

    assert isinstance(agent, AgentExecutor)

    chat_history = StreamlitChatMessageHistory(key=_ST_CHAT_HiSTORY_KEY)
    st.sidebar.button('Clear Chat', on_click=lambda: chat_history.clear())

    # this makes columns only as wide as are the buttons, see https://stackoverflow.com/a/77332142
    st.markdown("""
            <style>
                div[data-testid="column"] {
                    width: fit-content !important;
                    flex: unset;
                }
                div[data-testid="column"] * {
                    width: fit-content !important;
                }
            </style>
            """, unsafe_allow_html=True)

    chat = st.container()
    with chat:
        def _describe():
            with chat:
                _call_agent(agent, 'Describe my database, do not include INFORMATION_SCHEMA in your answer.')
        
        def _suggest():
            with chat:
                _call_agent(agent, 'Come up with some example questions for my database.')
        
        def _analyze():
            with chat:
                _call_agent(agent, 'Analyze my database. List 5 examples of transformations that can be performed, giving examples of specific tables for each, but not queries.')
                
        placeholder = st.empty()
        
        if len(chat_history.messages) == 0:
            chat_history.add_ai_message(ai_intro)
        
            col1, col2, col3 = st.columns(3)
            col1.button('Describe My Database',
                    on_click=_describe,
                    use_container_width=True)
            col2.button('Example Questions',
                        on_click=_suggest,
                        use_container_width=True)
            col3.button('Analyze & Suggest Ops',
                on_click=_analyze,
                use_container_width=True)

        for msg in chat_history.messages:
            with placeholder:
                st.chat_message(msg.type).write(msg.content)
            
    if user_input := st.chat_input():
        with chat:
            st.session_state.pop(_ST_TRANS_QUERY, None)
            st.chat_message('user').write(user_input)
            response = _call_agent(agent, user_input)
            st.chat_message('ai').write(response['output'])

    # get the output of the last message from the agent
    if len(chat_history.messages) > 1:
        last_output_message = chat_history.messages[-1].content
        if re.findall(r'```sql\n(.*?)\n```', last_output_message, re.DOTALL):
            with chat:
                col1, col2 = st.columns(2)

            def _execute_sql_handler():
                with chat:
                    _call_agent(agent, 'Run the last query!')

            def _create_transformation_handler():
                st.session_state[_ST_TRANS_QUERY] = query

            query = re.findall(r'```sql\n(.*?)\n```', last_output_message, re.DOTALL)[0]
            col1.button(
                'Execute SQL',
                on_click=_execute_sql_handler,
                use_container_width=True,
                disabled=bool(st.session_state.get(_ST_TRANS_QUERY)))
            col2.button(
                'Create Transformation',
                on_click=_create_transformation_handler,
                use_container_width=True,
                disabled=bool(st.session_state.get(_ST_TRANS_QUERY)))

    if st.session_state.get(_ST_TRANS_QUERY):
        query = st.session_state.get(_ST_TRANS_QUERY)
        with chat:
            with st.form(key='transformation_details_form', clear_on_submit=False):
                text_inputs = st.empty()
                col1, col2 = st.columns(2)
                submitted = col1.form_submit_button('Create')
                cancelled = col2.form_submit_button('Cancel')

                if _ST_TRANS_DETAILS not in st.session_state:
                    with text_inputs.container():
                        st.text_input('Transformation name', disabled=True)
                        st.text_area('Transformation description', disabled=True)
                        st.text_input('Output table name', disabled=True)
                        with st.spinner('Preparing transformation details ...'):
                            st.session_state[_ST_TRANS_DETAILS] = _generate_config_details(
                                chat_history.messages[-2:], model_current)
                        text_inputs.empty()

                with text_inputs.container():
                    tr_name = st.text_input(
                        'Transformation name', st.session_state[_ST_TRANS_DETAILS]['ai_tr_name'])
                    tr_description = st.text_area(
                        'Transformation description', st.session_state[_ST_TRANS_DETAILS]['ai_tr_description'])
                    tr_output_table = st.text_input(
                        'Output table name', st.session_state[_ST_TRANS_DETAILS]['ai_output_table'])

            if submitted:
                try:
                    response = create_snowflake_transformation(
                        sql_query=query, name=tr_name, description=tr_description, output_table_name=tr_output_table)
                    chat_history.add_ai_message(
                        f'Created transformation [{tr_name}]({get_transformation_url(response)})')

                except RequestException as rqe:
                    chat_history.add_ai_message(
                        f'Failed to created transformation `{tr_name}`.\n'
                        f'```json{json.dumps(rqe.response.json(), ensure_ascii=False, indent=2)}```')

                st.session_state.pop(_ST_TRANS_QUERY)
                st.session_state.pop(_ST_TRANS_DETAILS)
                st.rerun()

            if cancelled:
                st.session_state.pop(_ST_TRANS_QUERY)
                st.session_state.pop(_ST_TRANS_DETAILS)
                st.rerun()


app()