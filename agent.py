from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType

def create_db(conn_string):
    db = SQLDatabase.from_uri(conn_string)
    return db

def create_toolkit(llm, db):
    toolkit = SQLDatabaseToolkit(llm=llm, db=db, view_intermediate_results=True, view_messages=True, view_sql=True,  )
    return toolkit

def create_agent(toolkit, llm, custom_tool_list, memory):
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=50,
        extra_tools=custom_tool_list,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        memory=memory
    )
    return agent_executor

if __name__ == '__main__':
    create_agent()