import streamlit as st

from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
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
toolkit = SQLDatabaseToolkit(llm=OpenAI(temperature=0), db=db)


agent_executor = create_sql_agent(
    llm=OpenAI(temperature=0),
    toolkit=toolkit,
    verbose=True
)


question = st.text_input("Ask a question about your data", key="question")
if st.button("Ask"):
    answer = agent_executor.run(question)
    st.write(answer)
    