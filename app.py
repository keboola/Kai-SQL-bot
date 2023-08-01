import streamlit as st

from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.agents import AgentExecutor
import os

from src.workspace_connection.workspace_connection import connect_to_snowflake
from src.keboola_storage_api.connection import _add_connection_form
st.set_page_config(page_title="Kai SQL Bot Demo", page_icon=":robot:")
st.image('static/keboola_logo.png', width=400)
st.header("Kai SQL Bot Demo ")

st.markdown(
    """
    This is a demo of Kai, a SQL bot that can answer questions about your data.
    """
)

conn_method = st.selectbox("Choose a connection method", ["Snowflake DB Credentials",
                                                          "Keboola Storage API Token",
                                                           "Demo Database"])

if conn_method == "Snowflake DB Credentials":
    st.markdown(
        """
        Enter your Snowflake DB credentials below.
        """
    )
    connect_to_snowflake()
   
elif conn_method == "Keboola Storage API Token":
    st.markdown(
        """
        Enter your Keboola Storage API Token below.
        """
    )
    _add_connection_form()

    

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
print("DB===", db)
toolkit = SQLDatabaseToolkit(llm=OpenAI(temperature=0), db=db)

agent_executor = create_sql_agent(
    llm=OpenAI(temperature=0),
    toolkit=toolkit,
    verbose=True
)

from sqlalchemy.dialects import registry
registry.load("snowflake")
conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
db = SQLDatabase.from_uri(conn_string)
