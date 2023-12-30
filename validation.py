import openai
import streamlit as st
import os

import json


from langchain.memory import StreamlitChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory 

from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.prompts import PromptTemplate
from langchain.evaluation import load_evaluator
from src.workspace_connection.workspace_connection import initialize_connection
from agent import create_agent
from few_shot_examples import custom_tool_list

memory = ConversationBufferMemory()

conn_string = initialize_connection()

llm = ChatOpenAI(model="gpt-4-1106-preview", temperature=0,streaming=True)

agent_executor = create_agent(conn_string=conn_string, llm=llm, custom_tool_list=custom_tool_list, memory=memory)


