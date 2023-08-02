import streamlit as st
from streamlit_chat import message


from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor
import os

from src.workspace_connection.workspace_connection import connect_to_snowflake
from src.keboola_storage_api.connection import _add_connection_form
from sqlalchemy.dialects import registry
registry.load("snowflake")

st.set_page_config(page_title="Kai SQL Bot Demo", page_icon=":robot:")
st.image('static/keboola_logo.png', width=400)
st.header("Kai SQL Bot Demo ")

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

account_identifier = st.secrets["account_identifier"]
user = st.secrets["user"]
password = st.secrets["password"]
database_name = st.secrets["database_name"]
schema_name = st.secrets["schema_name"]
warehouse_name = st.secrets["warehouse_name"]
role_name = st.secrets["role_name"]

conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
db = SQLDatabase.from_uri(conn_string)
st.write("DB===", db)
toolkit = SQLDatabaseToolkit(llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0), db=db)


agent_executor = create_sql_agent(
    llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0),
    toolkit=toolkit,
    verbose=True
)


if "generated" not in st.session_state:
    st.session_state["generated"] = []

if "past" not in st.session_state:
    st.session_state["past"] = []


def get_text():
    input_text = st.text_input("You: ", "Hello, what are you capable of doing?", key="input")
    return input_text


user_input = get_text()

if user_input:
    output = agent_executor.run(input=user_input)

    st.session_state.past.append(user_input)
    st.session_state.generated.append(output)

if st.session_state["generated"]:

    for i in range(len(st.session_state["generated"]) - 1, -1, -1):
        message(st.session_state["generated"][i], key=str(i))
        message(st.session_state["past"][i], is_user=True, key=str(i) + "_user")


    