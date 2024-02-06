import streamlit as st
from langchain.sql_database import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit


class DatabaseConnection:
    def __init__(self, account_identifier=None, user=None, password=None, 
                 database_name=None, schema_name=None, warehouse_name=None, role_name=None):
        self.account_identifier = account_identifier or st.secrets["account_identifier"]
        self.user = user or st.secrets["user"]
        self.password = password or st.secrets["password"]
        self.database_name = database_name or st.secrets["database_name"]
        self.schema_name = schema_name or st.secrets["schema_name"]
        self.warehouse_name = warehouse_name or st.secrets["warehouse_name"]
        self.role_name = role_name or st.secrets["role_name"]

    def create_connection_string(self):
        conn_string = (f"snowflake://{self.user}:{self.password}"
                       f"@{self.account_identifier}/{self.database_name}/{self.schema_name}"
                       f"?warehouse={self.warehouse_name}&role={self.role_name}")
        return conn_string

    def create_db(self):
        conn_string = self.create_connection_string()
        db = SQLDatabase.from_uri(conn_string)
        return db

    def create_toolkit(self, llm):
        db = self.create_db()
        toolkit = SQLDatabaseToolkit(llm=llm, db=db)
        return toolkit
