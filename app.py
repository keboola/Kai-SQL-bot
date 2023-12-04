import json
import os
import re

import openai
import pandas as pd
import requests
import sqlalchemy
import streamlit as st
from streamlit_ace import st_ace

from langchain.memory import StreamlitChatMessageHistory, ConversationBufferMemory
from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.prompts import PromptTemplate
from langchain.callbacks import StreamlitCallbackHandler, HumanApprovalCallbackHandler

from src.workspace_connection.workspace_connection import connect_to_snowflake
from prompts import frosty_gen_sql, custom_gen_sql

# Setting up the Streamlit page
image_path = os.path.dirname(os.path.abspath(__file__))
st.image(image_path+'/static/keboola_logo.png', width=200)
home_title = "Kai SQL Bot"
st.markdown(f"""# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>""", unsafe_allow_html=True)

# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY
msgs = StreamlitChatMessageHistory(key="chat_messages")
memory = ConversationBufferMemory(chat_memory=msgs)

# Model selection for the chatbot
model_selection = st.sidebar.selectbox("Choose a model", ['gpt-3.5-turbo-16k', 'gpt-4'], help="Select the model you want to use for the chatbot.")
llm = ChatOpenAI(model=model_selection, temperature=0, streaming=True) if model_selection != 'default' else OpenAI(temperature=0, streaming=True)

# Initialize database connection
def initialize_connection():
    account_identifier = st.secrets["account_identifier"]
    user = st.secrets["user"]
    password = st.secrets["password"]
    database_name = st.secrets["database_name"]
    schema_name = st.secrets["schema_name"]
    warehouse_name = st.secrets["warehouse_name"]
    role_name = st.secrets["user"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=llm, db=db)
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=50,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        memory=memory
    )
    return agent_executor, conn_string

agent_executor, conn_string = initialize_connection()

# Chat interface
if len(msgs.messages) == 0:
    msgs.add_ai_message("Hello, I'm Kai, your AI SQL Bot. I'm here to assist you with SQL queries. What can I do for you?")
for msg in msgs.messages:
    st.chat_message(msg.type).write(msg.content)
if prompt := st.chat_input():
    msgs.add_user_message(prompt)
    st.chat_message("user").write(prompt)
    st_callback = StreamlitCallbackHandler(st.container(), expand_new_thoughts=True)
    prompt_formatted = custom_gen_sql.format(context=prompt)
    try:
        response = agent_executor.run(input=prompt_formatted, callbacks=[st_callback], memory=memory)
    except ValueError as e:
        response = str(e)
        if not response.startswith("Could not parse LLM output: `"):
            raise e
        response = response.removeprefix("Could not parse LLM output: `").removesuffix("`")
    msgs.add_ai_message(response)
    st.chat_message("Kai").write(response)

# SQL Execution and Feedback Section
with st.container():
    if len(msgs.messages) > 1:
        last_output_message = msgs.messages[-1].content
        sql_matches = re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL)
        if sql_matches:
            if st.button("Execute SQL"):
                engine = sqlalchemy.create_engine(conn_string)
                for sql in sql_matches:
                    try:
                        df = pd.DataFrame(engine.execute(sql).fetchall())
                        st.sidebar.write("Results")
                        st.sidebar.dataframe(df)
                    except Exception as e:
                        st.write(e)

        def clear_chat():
            msgs.clear()
        st.sidebar.button("Clear Chat", on_click=clear_chat)

        # Feedback buttons
        col_1, col_2 = st.columns([1, 5])
        feedback_counts = {"thumbs_up": 0, "thumbs_down": 0}
        with col_1:
            if st.button("👍"):
                feedback_counts["thumbs_up"] += 1
        with col_2:
            if st.button("👎"):
                feedback_counts["thumbs_down"] += 1

# Additional UI Components and Logging
#with st.container():
    # [Add any additional UI components and logging logic here]

