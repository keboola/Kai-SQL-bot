import openai
import streamlit as st
import pandas as pd
import json
import datetime
import concurrent.futures
import os

from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.evaluation import load_evaluator
from langchain.callbacks import LLMonitorCallbackHandler

from src.database_connection.database_connection import DatabaseConnection
from agent import SQLAgentCreator
from few_shot_examples import custom_tool_list
from prompts import custom_gen_sql

#get current datetime as a unix timestamp
current_time = datetime.datetime.now().timestamp()

lunary_callback = LLMonitorCallbackHandler(app_id=os.getenv("LUNARY_APP_ID"))
lunary_user_id = f"ValidationRun-{current_time}"

memory = ConversationBufferMemory()

llm = ChatOpenAI(model="gpt-4-1106-preview", temperature=0,streaming=True)

db_conn = DatabaseConnection(os.getenv("ACCOUNT_IDENTIFIER"), os.getenv("USER"), os.getenv("PASSWORD"),
                    os.getenv("DATABASE_NAME"), os.getenv("SCHEMA_NAME"), os.getenv("WAREHOUSE_NAME"), os.getenv("ROLE_NAME"))

toolkit = db_conn.create_toolkit(llm)

agent_creator = SQLAgentCreator(toolkit=toolkit, llm=llm, custom_tool_list=custom_tool_list, memory=memory)

evaluator = load_evaluator("labeled_pairwise_string")
with open('validation.json', 'r') as f:
    data = json.load(f)

print("data loaded")

n = 0
evaluation_output = {}

def process_data(item):
    agent_executor = agent_creator.create_agent()
    n = item[0]
    data = item[1]
    print(f"Question: {data['question']}")
    prompt_formatted = custom_gen_sql.format(context=data['question'])

    try:
        response = agent_executor.run(input=prompt_formatted, memory=memory, callbacks=[lunary_callback], metadata={ "agentName": "KaiSQLBot", "user_id": lunary_user_id})
    except ValueError as e:
        response = str(e)
        if not response.startswith("Could not parse LLM output: `"):
            raise e
        response = response.removeprefix("Could not parse LLM output: `").removesuffix("`")
    except openai.InvalidRequestError as e:
        response = str(e)
        if response.startswith("InvalidRequestError: This model's maximum context length%"):
            response = "Model context length exceeded. Please try again."

    evaluation = evaluator.evaluate_string_pairs(
        prediction=response, # new agent run
        prediction_b=data['answer'], # baseline
        input=data['question'],
        reference=data['answer']
    )
    print(f"Baseline: {data['answer']}")
    print(f"New Output: {response}")
    print(evaluation)

    return {
        "n": n,
        "model": 'GPT-4-Turbo',
        "agent_type": 'OPENAI_FUNCTIONS',
        "question": data['question'],
        "baseline_answer": data['answer'],
        "prediction (new agent run)": response,
        "evaluation": evaluation
    }
    

evaluation_output = {}
with concurrent.futures.ThreadPoolExecutor() as executor:
    results = executor.map(process_data, enumerate(data))

    for result in results:
        evaluation_output[result["n"]] = result

print("evaluation complete")

df = pd.DataFrame.from_dict(evaluation_output, orient='index')

#df.to_csv('evaluation_output.csv', index=False)
