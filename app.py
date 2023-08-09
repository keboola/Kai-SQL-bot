import streamlit as st

st.title("Hello Anya")
st.subheader("Aloha!")
api_key = st.text_input('API Token', 'Enter OpenAI API Token', type="password")

from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.agents import AgentExecutor
import os
import pandas as pd
import numpy as np


os.environ["OPENAI_API_KEY"] = st.secrets['openai_key']

account_identifier = 'keboola.west-europe.azure'
user = st.secrets['user']
password = st.secrets['password']
database_name = st.secrets['database_name']
schema_name = st.secrets['schema_name']
warehouse_name = st.secrets['warehouse_name']
role_name = st.secrets['role_name']

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


userquery = st.text_input('Enter your query')
if st.button("run"):
    st.write(agent_executor.run(userquery))
    
"Hoy there"

add_selectbox = st.sidebar.selectbox(
    'How would you like to be contacted?',
    ('Email', 'Home phone', 'Mobile phone')
)

# Add a slider to the sidebar:
add_slider = st.sidebar.slider(
    'Select a range of values',
    0.0, 100.0, (25.0, 75.0)
)

streamlit==1.18
streamlit-authenticator==0.2.1
hydralit-components==1.0.10
git+https://github.com/keboola/sapi-python-client.git
st-click-detector==0.1
vega_datasets==0.9.0
pandas==1.2.5
altair==4.1.0