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
from prompts import en_prompt_template

print("Validation page")

models = ['gpt-3.5-turbo-instruct', 'gpt-3.5-turbo-16k', 'gpt-4']


llm = ChatOpenAI(model=models[1], temperature=0)

def initialize_connection():
    account_identifier = os.environ["account_identifier"]
    user = os.environ["user"]
    password = os.environ["password"]
    database_name = os.environ["database_name"]
    schema_name = os.environ["schema_name"]
    warehouse_name = os.environ["warehouse_name"]
    role_name = os.environ["user"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=llm, db=db)
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    )
    return agent_executor, conn_string

agent_executor, conn_string = initialize_connection()   

gen_sql_prompt = en_prompt_template

# grab the validation.json file and loop through it to call agent_executor.run
# for each validation example

evaluator = load_evaluator("string_distance")
with open('validation.json', 'r') as f:
    data = json.load(f)

print('Data loaded')

for i in range(len(data)):
    print(f"Question: {data[i]['question']}")
    prompt_formatted = gen_sql_prompt.format(context=data[i]['question'])
    try:
        response = agent_executor.run(input=prompt_formatted, memory=memory)
    except ValueError as e:
        response = str(e)
        if not response.startswith("Could not parse LLM output: `"):
            raise e
        response = response.removeprefix("Could not parse LLM output: `").removesuffix("`")

    evaluation = evaluator.evaluate_strings(
    prediction=response,
    reference=data[i]['answer'],
    )

    print(f"Answer: {data[i]['answer']}")
    print(f"Prediction: {response}")
    print(evaluation)

