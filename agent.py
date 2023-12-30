from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType

class SQLAgentCreator:
    def __init__(self, llm, toolkit, custom_tool_list=None, memory=None):
        self.llm = llm
        self.toolkit = toolkit
        self.custom_tool_list = custom_tool_list or []
        self.memory = memory

    def create_agent(self):
        agent_executor = create_sql_agent(
            llm=self.llm,
            toolkit=self.toolkit,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=50,
            extra_tools=self.custom_tool_list,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            memory=self.memory
        )
        return agent_executor
