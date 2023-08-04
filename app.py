import streamlit as st
from streamlit_chat import message


from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.agents import AgentExecutor
import os
import requests
from src.workspace_connection.workspace_connection import connect_to_snowflake, snowflake_connection_user_input

#from sqlalchemy.dialects import registry
#registry.load("snowflake")

st.set_page_config(page_title="Kai SQL Bot Demo", page_icon=":robot:")
path = os.path.dirname(os.path.abspath(__file__))
st.image(path+'/static/keboola_logo.png', width=400)
st.header("Kai SQL Bot Demo ")

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

conn_method = st.selectbox("Connection Method", ["Demo Database", "Snowflake Database Connection"])


if conn_method == "Snowflake Database Connection":
    connect_to_snowflake()
    conn_string = f"snowflake://{st.session_state['user']}:{st.session_state['password']}@{st.session_state['account']}/{st.session_state['database']}/{st.session_state['schema']}?warehouse={st.session_state['warehouse']}&role={st.session_state['user']}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0), db=db)

else:
    st.write("Using Demo Database") 
    account_identifier = st.secrets["account_identifier"]
    user = st.secrets["user"]
    password = st.secrets["password"]
    database_name = st.secrets["database_name"]
    schema_name = st.secrets["schema_name"]
    warehouse_name = st.secrets["warehouse_name"]
    role_name = st.secrets["role_name"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=OpenAI(temperature=0), db=db)


agent_executor = create_sql_agent(
    llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0),
    toolkit=toolkit,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=100,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)


if "generated" not in st.session_state:
    st.session_state["generated"] = []

if "past" not in st.session_state:
    st.session_state["past"] = []


def get_text():
    input_text = st.text_input("You: ", "Hello, what are you capable of doing?", key="input")
    return input_text

headers = {'Content-Type': 'application/json'}

user_input = get_text()

if user_input:
    output = agent_executor.run(input=user_input)

    st.session_state.past.append(user_input)
    st.session_state.generated.append(output)

    log_data = "User: " + user_input + "\n" + "Kai: " + output + "\n"

    r = requests.post(st.secrets["url"], data=log_data, headers=headers)


if st.session_state["generated"]:

    for i in range(len(st.session_state["generated"]) - 1, -1, -1):
        message(st.session_state["generated"][i], key=str(i))
        message(st.session_state["past"][i], is_user=True, key=str(i) + "_user")


    
   
