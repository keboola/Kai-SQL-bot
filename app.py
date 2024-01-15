import os
import re

import openai
import streamlit as st
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, StreamlitChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder, PromptTemplate, \
    SystemMessagePromptTemplate
from langchain_core.runnables import Runnable
from llama_hub.tools.waii import WaiiToolSpec
from streamlit_feedback import streamlit_feedback

from chat import ChatDisplay
from create import create_snowflake_transformation
from prompts import pandy_gen_sql

image_path = os.path.dirname(os.path.abspath(__file__))
st.image(image_path+'/static/keboola_logo.png', width=200)
home_title = 'Kai SQL Bot'  # Replace with your title
st.markdown(f'''# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>''', unsafe_allow_html=True)

# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY

model_selection = st.sidebar.selectbox(
    'Choose a model',
    ['gpt-4-1106-preview', 'gpt-4', 'gpt-3.5-turbo-16k'],
    help='Select the model you want to use for the chatbot.'
)


llm = ChatOpenAI(model=model_selection, temperature=0, streaming=True)

conn_string = (f'snowflake://{st.secrets["user"]}@{st.secrets["account_identifier"]}/{st.secrets["database_name"]}'
               f'?role={st.secrets["user"]}&warehouse={st.secrets["warehouse_name"]}')

msgs_history = StreamlitChatMessageHistory(key='sql-bot-message-history-in-streamlit')
memory = ConversationBufferMemory(memory_key='chat_history', chat_memory=msgs_history, return_messages=True)

waii_api_key = st.secrets['waii_prod_api_key']
waii_tool = WaiiToolSpec(
    url='https://tweakit.waii.ai/api/',
    # API Key of Waii (not OpenAI API key)
    api_key=waii_api_key,
    database_key=conn_string,
    verbose=True
)
tools = waii_tool.to_tool_list()
converted_langchain_tools = [t.to_langchain_tool() for t in tools]

tool_to_description = {
    # get_answer and its description
    'get_answer': '''Generate a SQL query and run it against the database, returning the summarization of the answer''',

    # generate_query_only and its description
    'generate_query_only': '''Generate a SQL query and NOT run it, returning the query. If you need to get answer, 
    you should use get_answer instead.''',

    # run_query and its description
    'run_query': '''Run an existing (no need to generate a new one) SQL query, and get summary of the result''',

    # describe_dataset and its description
    'describe_dataset': '''Describe a dataset (no matter if it is a table or schema), returning the summarization 
    of the answer. Example questions like: "describe the dataset", "what the schema is about", "example question 
    for the table xxx", etc. When both schema and table are None, describe the whole database.

    If asked question needs a query against information_schema to answer the question, such as "how many tables 
    in the database / how many column of each table, etc." use `get_answer` instead of `describe_dataset`'''
}

langchain_tools = []
for t in converted_langchain_tools:
    if t.name in tool_to_description:
        t.description = tool_to_description[t.name]
        langchain_tools.append(t)

prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate(prompt=pandy_gen_sql),
    MessagesPlaceholder(variable_name='chat_history'),
    HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['input'], template='{input}')),
    MessagesPlaceholder(variable_name='agent_scratchpad')
])
agent: Runnable = create_openai_tools_agent(llm, langchain_tools, prompt=prompt)
agent_executor = AgentExecutor(
    agent=agent, tools=langchain_tools, verbose=True, memory=memory
)

# Create a dictionary to store feedback counts
feedback_counts = {'thumbs_up': 0, 'thumbs_down': 0}


# Function to handle user feedback
def handle_feedback(feedback_type):
    feedback_counts[feedback_type] += 1


chat_display = ChatDisplay(agent_executor)
chat_display.display_chat()

view_messages = st.sidebar.expander('View the message contents in session state')

# get the output of the last message from the agent 
if len(msgs_history.messages) > 1:
    last_output_message = msgs_history.messages[-1].content
    
    col1, col2, col3 = st.columns(3)
    # def execute_sql():
    #     sql_matches = re.findall(r'```sql\n(.*?)\n```', last_output_message, re.DOTALL)
    #     for sql in sql_matches:
    #         try:
    #             # connect to snowflake using sqlalchemy engine and execute the sql query
    #             engine = sqlalchemy.create_engine(conn_string)
    #             df = engine.execute(sql).fetchall()
    #             df = pd.DataFrame(df)
    #             st.sidebar.write('Results')
    #             st.sidebar.dataframe(df)
    #         except Exception as e:
    #             st.write(e)
    #             st.write('invalid_query')

    if re.findall(r'```sql\n(.*?)\n```', last_output_message, re.DOTALL):
        query = re.findall(r'```sql\n(.*?)\n```', last_output_message, re.DOTALL)[0]
        # col2.button('Execute SQL', on_click=execute_sql, use_container_width=True)
        with st.sidebar.container():
            st.write('❄️ Create Snowflake Transformation in Keboola')
            create_snowflake_transformation(query)
    
    def clear_chat():
        msgs_history.clear()

    col3.button('Clear Chat', on_click=clear_chat, use_container_width=True)
    with col1:
        feedback = streamlit_feedback(feedback_type='thumbs', align='center')

    # Create two columns with custom widths
    # Apply custom CSS to reduce margin between columns
    st.markdown(
        '''
        <style>
        .st-b3 {
            margin-left: -10px; /* Adjust the negative margin as needed */
        }
        </style>
        ''',
        unsafe_allow_html=True,
    )
    with view_messages:
        view_messages.json(st.session_state.get('sql-bot-message-history-in-streamlit', []))
