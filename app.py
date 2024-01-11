import openai
import re
import streamlit as st
import os
import sqlalchemy
import pandas as pd

from streamlit_feedback import streamlit_feedback
from create import create_snowflake_transformation
from langchain.agents import AgentExecutor, create_openai_tools_agent
from llama_hub.tools.waii import WaiiToolSpec
from langchain.chat_models import ChatOpenAI
from langchain.memory import StreamlitChatMessageHistory, ConversationBufferMemory

from langchain import hub
from waii_sdk_py import WAII
from src.database_connection.database_connection import DatabaseConnection
from agent import SQLAgentCreator
from chat import ChatDisplay
from few_shot_examples import custom_tool_list

image_path = os.path.dirname(os.path.abspath(__file__))
st.image(image_path+'/static/keboola_logo.png', width=200)
home_title = "Kai SQL Bot"  # Replace with your title
st.markdown(f"""# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>""", unsafe_allow_html=True)
# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY

model_selection = st.sidebar.selectbox("Choose a model", ['gpt-4-1106-preview', 'gpt-4', 'gpt-3.5-turbo-16k'], help="Select the model you want to use for the chatbot.")
llm = ChatOpenAI(model=model_selection, temperature=0, streaming=True)

#ascend_db_conn = DatabaseConnection(st.secrets["ascend_climbing"]["account_identifier"], st.secrets["ascend_climbing"]["user"], st.secrets["ascend_climbing"]["password"],
#                                    st.secrets["ascend_climbing"]["database_name"], st.secrets["ascend_climbing"]["schema_name"], st.secrets["ascend_climbing"]["warehouse_name"], st.secrets["ascend_climbing"]["role_name"])

#db_conn = DatabaseConnection(st.secrets["shopify_ecommerce_db"]["account_identifier"], st.secrets["shopify_ecommerce_db"]["user"], st.secrets["shopify_ecommerce_db"]["password"],
#                    st.secrets["shopify_ecommerce_db"]["database_name"], st.secrets["shopify_ecommerce_db"]["schema_name"], st.secrets["shopify_ecommerce_db"]["warehouse_name"], st.secrets["shopify_ecommerce_db"]["role_name"])

#db_conn = DatabaseConnection(st.secrets["account_identifier"], st.secrets["user"], st.secrets["password"],
#                    st.secrets["database_name"], st.secrets["schema_name"], st.secrets["warehouse_name"], st.secrets["role_name"])

#toolkit = db_conn.create_toolkit(llm)

conn_string = f"snowflake://{st.secrets['user']}@{st.secrets['account_identifier']}/{st.secrets['database_name']}?role={st.secrets['user']}&warehouse={st.secrets['warehouse_name']}"

db_conn = conn_string
msgs_history = StreamlitChatMessageHistory(key="messages") # the history is def not working ahah
memory = ConversationBufferMemory(chat_memory=msgs_history)

#agent_creator = SQLAgentCreator(toolkit=toolkit, llm=llm, custom_tool_list=custom_tool_list, memory=memory)
#agent_executor = agent_creator.create_agent()

waii_api_key = st.secrets['waii_prod_api_key']
waii_tool = WaiiToolSpec(
    url="https://tweakit.waii.ai/api/",
    # API Key of Waii (not OpenAI API key)
    api_key=waii_api_key,
    database_key=db_conn,
    verbose=True
)
tools = waii_tool.to_tool_list()
converted_langchain_tools = [t.to_langchain_tool() for t in tools]

tool_to_description = {
    # get_answer and its description
    "get_answer":"""Generate a SQL query and run it against the database, returning the summarization of the answer""",

    # generate_query_only and its description
    "generate_query_only":"""Generate a SQL query and NOT run it, returning the query. If you need to get answer, you should use get_answer instead.""",

     # run_query and its description
     "run_query": """Run an existing (no need to generate a new one) SQL query, and get summary of the result""",

     # describe_dataset and its description
     "describe_dataset": """Describe a dataset (no matter if it is a table or schema), returning the summarization of the answer.
Example questions like: "describe the dataset", "what the schema is about", "example question for the table xxx", etc.
When both schema and table are None, describe the whole database.

If asked question needs a query against information_schema to answer the question, such as "how many tables in the database / how many column of each table, etc." use `get_answer` instead of `describe_dataset`"""}

langchain_tools = []
for t in converted_langchain_tools:
  if t.name in tool_to_description:
    t.description = tool_to_description[t.name]
    langchain_tools.append(t)

prompt = hub.pull("hwchase17/openai-tools-agent")
agent = create_openai_tools_agent(llm, langchain_tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=langchain_tools, verbose=True)

# Create a dictionary to store feedback counts
feedback_counts = {"thumbs_up": 0, "thumbs_down": 0}

# Function to handle user feedback
def handle_feedback(feedback_type):
    feedback_counts[feedback_type] += 1

chat_display = ChatDisplay(agent_executor, memory)
chat_display.display_chat()

msgs = chat_display.msgs

view_messages = st.sidebar.expander("View the message contents in session state")

# get the output of the last message from the agent 
if len(msgs.messages) > 1:
    last_output_message = msgs.messages[-1].content    
    
    col1, col2, col3 = st.columns(3)
    def execute_sql():    
        sql_matches = re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL)
        for sql in sql_matches:
            try:
                #connect to snowflake using sqlalchemy engine and execute the sql query
                engine = sqlalchemy.create_engine(conn_string)
                df = engine.execute(sql).fetchall()
                df = pd.DataFrame(df)
                st.sidebar.write("Results")
                st.sidebar.dataframe(df)
            except Exception as e:
                st.write(e)
                st.write("invalid_query")

    if re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL):
        query = re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL)[0]
        col2.button("Execute SQL", on_click=execute_sql, use_container_width=True)
        with st.sidebar.container():
            st.write("❄️ Create Snowflake Transformation in Keboola")
            create_snowflake_transformation(query)
    
    def clear_chat():
        msgs.clear() 

    col3.button("Clear Chat", on_click=clear_chat, use_container_width=True)
    with col1:
        feedback = streamlit_feedback(feedback_type="thumbs", align='center')

    # Create two columns with custom widths
##    col_1, col_2 = st.columns([1, 5])
    # Apply custom CSS to reduce margin between columns
    st.markdown(
        """
        <style>
        .st-b3 {
            margin-left: -10px; /* Adjust the negative margin as needed */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Display thumbs-up button in the first column
##    with col_1:
##        if st.button("👍"):
##            handle_feedback("thumbs_up")
    # Display thumbs-down button in the second column
##    with col_2:
##        if st.button("👎"):
##            handle_feedback("thumbs_down")
##    if feedback_counts["thumbs_up"] > feedback_counts["thumbs_down"]:
##        feedback = "positive"
##    elif feedback_counts["thumbs_up"] < feedback_counts["thumbs_down"]:
##        feedback = "negative"
##    else:
        # If both counts are equal or both are 0, set a default feedback
##        feedback = "neutral"
    #log_data = "User: " + last_user_message["content"] + "\n" + "Kai: " + last_output_message["content"] + "\n" + "feedback: " + feedback + "\n"
    headers = {'Content-Type': 'application/json'}
    with view_messages: """
Memory initialized with:
```python
msgs = StreamlitChatMessageHistory(key="langchain_messages")
memory = ConversationBufferMemory(chat_memory=msgs)
```

Contents of `st.session_state.langchain_messages`:
"""
view_messages.json(st.session_state.messages)