import json
import os
import re
from typing import Any, List, Mapping

import openai
import streamlit as st
from langchain.agents import AgentExecutor
from langchain.callbacks import FileCallbackHandler
from langchain.callbacks.streamlit import StreamlitCallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from llmonitor.langchain import LLMonitorCallbackHandler
from requests import RequestException

import prompts
from agent import AgentBuilder
from create import create_snowflake_transformation, get_transformation_url

_ST_CHAT_HiSTORY_KEY = 'sql-bot-message-history-in-streamlit'
_ST_TRANS_QUERY = 'transformation_query'
_ST_TRANS_DETAILS = 'transformation_details'


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


def _generate_config_details(chat_history: List[BaseMessage], model: AgentBuilder.Model) -> Mapping[str, Any]:
    model = ChatOpenAI(model_name=model.value, temperature=0)
    parser = JsonOutputParser(pydantic_object=_AIConfig)
    chain = prompts.tr_config_prompt | model | parser

    return chain.invoke({
        'format_instructions': parser.get_format_instructions(),
        'chat_history': chat_history[-2:],  # take up to 2
    })


def app():
    openai.api_key = st.secrets.OPENAI_API_KEY

    image_path = os.path.dirname(os.path.abspath(__file__))
    st.image(image_path+'/static/keboola_logo.png', width=200)
    home_title = 'Kai SQL Bot'  # Replace with your title
    st.markdown(f'# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>', unsafe_allow_html=True)

    st.sidebar.markdown(f'## {home_title} Settings')
    model_current = AgentBuilder.Model.from_text(st.sidebar.selectbox(
        label='Choose a model',
        options=[m.value for m in AgentBuilder.Model],
        help='Select the model you want to use for the chatbot.'
    ))
    model_last = AgentBuilder.Model.from_text(st.session_state.get('model'))
    toolkit_current = AgentBuilder.Toolkit.from_text(st.sidebar.selectbox(
        label='Choose tools',
        options=[t.value for t in AgentBuilder.Toolkit],
        help='Select the tools you want to use for the chatbot.'
    ))
    toolkit_last = AgentBuilder.Toolkit.from_text(st.session_state.get('toolkit'))

    if model_last != model_current or toolkit_last != toolkit_current:
        # reset the agent
        agent = (AgentBuilder()
                 .with_model(model_current)
                 .with_toolkit(toolkit_current)
                 .with_waii_api_key(st.secrets.WAII_API_KEY)
                 .with_snowflake(
                    username=st.secrets.SNFLK_USER, password=st.secrets.SNFLK_PASSWORD,
                    account_identifier=st.secrets.SNFLK_ACCOUNT_IDENTIFIER, database_name=st.secrets.SNFLK_DATABASE,
                    schema_name=st.secrets.SNFLK_SCHEMA, warehouse=st.secrets.SNFLK_WAREHOUSE
                 )
                 .build())
        st.session_state['agent'] = agent
        # store string to the session, using custom classes results in different type instances create after each
        # streamlit re-run and comparing the seemingly same class instances does not work then
        st.session_state['model'] = model_current.value
        st.session_state['toolkit'] = toolkit_current.value
    else:
        agent = st.session_state.agent

    assert isinstance(agent, AgentExecutor)

    agent_memory = agent.memory
    assert isinstance(agent_memory, ConversationBufferMemory)
    st.sidebar.button('Clear Chat', on_click=lambda: agent_memory.clear())

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
        if len(agent_memory.chat_memory.messages) == 0:
            agent_memory.chat_memory.add_ai_message(prompts.ai_intro)

        for msg in agent_memory.chat_memory.messages:
            st.chat_message(msg.type).write(msg.content)

    if user_input := st.chat_input():
        with chat:
            st.session_state.pop(_ST_TRANS_QUERY, None)
            st.chat_message('user').write(user_input)
            response = _call_agent(agent, user_input)
            st.chat_message('ai').write(response['output'])

    # get the output of the last message from the agent
    if len(agent_memory.chat_memory.messages) > 1:
        last_output_message = agent_memory.chat_memory.messages[-1].content
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
                                agent_memory.chat_memory.messages, model_current)
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
                    agent_memory.chat_memory.add_ai_message(
                        f'Created transformation [{tr_name}]({get_transformation_url(response)})')

                except RequestException as rqe:
                    agent_memory.chat_memory.add_ai_message(
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
