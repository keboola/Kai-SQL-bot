from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType


def create_agent(conn_string, llm, custom_tool_list, memory):
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=llm, db=db, view_intermediate_results=True, view_messages=True)
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