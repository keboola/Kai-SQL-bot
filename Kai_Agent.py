# '''Kai Agent'''
# from typing import Any, Dict, List, Optional, Sequence
# from langchain.agents.agent import AgentExecutor, BaseSingleActionAgent
# from langchain.agents.agent_toolkits.sql.prompt import (
#     SQL_FUNCTIONS_SUFFIX,
#     SQL_PREFIX,
#     SQL_SUFFIX,
# )
# from langchain.agents.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
# from langchain.agents.agent_types import AgentType
# from langchain.agents.mrkl.base import ZeroShotAgent
# from langchain.agents.mrkl.prompt import FORMAT_INSTRUCTIONS
# from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
# from langchain.callbacks.base import BaseCallbackManager
# from langchain.chains.llm import LLMChain
# from langchain.prompts.chat import (
#     ChatPromptTemplate,
#     HumanMessagePromptTemplate,
#     MessagesPlaceholder,
# )
# from langchain.schema.language_model import BaseLanguageModel
# from langchain.schema.messages import AIMessage, SystemMessage
# from langchain.tools import BaseTool, Tool

# from langchain.agents.agent_toolkits.base import BaseToolkit
# from langchain.pydantic_v1 import Field
# from langchain.tools.sql_database.tool import (
#     InfoSQLDatabaseTool,
#     ListSQLDatabaseTool,
#     QuerySQLCheckerTool,
#     QuerySQLDataBaseTool,
# )
# from langchain.utilities.sql_database import SQLDatabase
'''
Playground for init agents from the lowest level, tried combining identities but so far
no luck.
    * Attempted to init a new agent as MultiAction and use this to give it the properties
    of both the sql agent and python agent.  
    * Attempted making class with history, and importing both of the agents into the
    class as args.
    * Tried modifying the SQLDatabaseToolkit, had problems getting anything to compile
    * Tried going back to the plan and excecute agent idea, but wasnt able to maintain memory. 
'''

# class create_Kai_Agent(BaseMultiActionAgent, BaseMemoryAgent):
#     def __init__(self):
#         super().__init__()
#         self.memory = {}

#     def create_SQL_Agent(
#         llm: BaseLanguageModel,
#         toolkit: SQLDatabaseToolkitMOD, 
#         agent_type: AgentType = AgentType.ZERO_SHOT_REACT_DESCRIPTION,
#         callback_manager: Optional[BaseCallbackManager] = None,
#         prefix: str = SQL_PREFIX,
#         suffix: Optional[str] = None,
#         format_instructions: str = FORMAT_INSTRUCTIONS,
#         input_variables: Optional[List[str]] = None,
#         top_k: int = 10,
#         max_iterations: Optional[int] = 15,
#         max_execution_time: Optional[float] = None,
#         early_stopping_method: str = "force",
#         verbose: bool = False,
#         agent_executor_kwargs: Optional[Dict[str, Any]] = None,
#         extra_tools: Sequence[BaseTool] = (),
#         **kwargs: Dict[str, Any],
#     ) -> AgentExecutor:
#         """Construct an SQL agent from an LLM and tools."""
#         tools = toolkit.get_tools() + list(extra_tools)
#         prefix = prefix.format(dialect=toolkit.dialect, top_k=top_k)
#         agent: BaseSingleActionAgent

#         if agent_type == AgentType.OPENAI_FUNCTIONS:
#             messages = [
#                 SystemMessage(content=prefix),
#                 HumanMessagePromptTemplate.from_template("{input}"),
#                 AIMessage(content=suffix or SQL_FUNCTIONS_SUFFIX),
#                 MessagesPlaceholder(variable_name="agent_scratchpad"),
#             ]
#             input_variables = ["input", "agent_scratchpad"]
#             _prompt = ChatPromptTemplate(input_variables=input_variables, messages=messages)

#             agent = OpenAIFunctionsAgent(
#                 llm=llm,
#                 prompt=_prompt,
#                 tools=tools,
#                 callback_manager=callback_manager,
#                 **kwargs,
#             )
#         else:
#             raise ValueError(f"Agent type {agent_type} not supported at the moment.")

#         return AgentExecutor.from_agent_and_tools(
#             agent=agent,
#             tools=tools,
#             callback_manager=callback_manager,
#             verbose=verbose,
#             max_iterations=max_iterations,
#             max_execution_time=max_execution_time,
#             early_stopping_method=early_stopping_method,
#             **(agent_executor_kwargs or {}),
#         )

# def create_pandas_dataframe_agent(
#     llm: BaseLanguageModel,
#     df: Any,
#     agent_type: AgentType = AgentType.ZERO_SHOT_REACT_DESCRIPTION,
#     callback_manager: Optional[BaseCallbackManager] = None,
#     prefix: Optional[str] = None,
#     suffix: Optional[str] = None,
#     input_variables: Optional[List[str]] = None,
#     verbose: bool = True,
#     return_intermediate_steps: bool = False,
#     max_iterations: Optional[int] = 15,
#     max_execution_time: Optional[float] = None,
#     early_stopping_method: str = "force",
#     agent_executor_kwargs: Optional[Dict[str, Any]] = None,
#     include_df_in_prompt: Optional[bool] = True,
#     number_of_head_rows: int = 5,
#     **kwargs: Dict[str, Any],
# ) -> AgentExecutor:
#     """Construct a pandas agent from an LLM and dataframe."""
#     agent: BaseSingleActionAgent
#     agent_type == AgentType.OPENAI_FUNCTIONS:
#         _prompt, tools = _get_functions_prompt_and_tools(
#             df,
#             prefix=prefix,
#             suffix=suffix,
#             input_variables=input_variables,
#             include_df_in_prompt=include_df_in_prompt,
#             number_of_head_rows=number_of_head_rows,
#         )
#         agent = OpenAIFunctionsAgent(
#             llm=llm,
#             prompt=prompt,
#             tools=tools,
#             callback_manager=callback_manager,
#             **kwargs,
#         )
#     return AgentExecutor.from_agent_and_tools(
#         agent=agent,
#         tools=tools,
#         callback_manager=callback_manager,
#         verbose=verbose,
#         return_intermediate_steps=return_intermediate_steps,
#         max_iterations=max_iterations,
#         max_execution_time=max_execution_time,
#         early_stopping_method=early_stopping_method,
#         **(agent_executor_kwargs or {}),
#     )

# # class SQLDatabaseToolkitMOD(BaseToolkit):
# #     """Toolkit for interacting with SQL databases."""

# #     db: SQLDatabase = Field(exclude=True)
# #     llm: BaseLanguageModel = Field(exclude=True)

# #     @property
# #     def dialect(self) -> str:
# #         """Return string representation of SQL dialect to use."""
# #         return self.db.dialect

# #     class Config:
# #         """Configuration for this pydantic object."""

# #         arbitrary_types_allowed = True

# #     def get_tools(self) -> List[BaseTool]:
# #         """Get the tools in the toolkit."""
# #         list_sql_database_tool = ListSQLDatabaseTool(db=self.db)
# #         info_sql_database_tool_description = (
# #             "Input to this tool is a comma-separated list of tables, output is the "
# #             "schema and sample rows for those tables. "
# #             "Be sure that the tables actually exist by calling "
# #             f"{list_sql_database_tool.name} first! "
# #             "Example Input: 'table1, table2, table3'"
# #         )
# #         info_sql_database_tool = InfoSQLDatabaseTool(
# #             db=self.db, description=info_sql_database_tool_description
# #         )
# #         query_sql_database_tool_description = (
# #             "Input to this tool is a detailed and correct SQL query, output is a "
# #             "result from the database. If the query is not correct, an error message "
# #             "will be returned. If an error is returned, rewrite the query, check the "
# #             "query, and try again. If you encounter an issue with Unknown column "
# #             f"'xxxx' in 'field list', using {info_sql_database_tool.name} "
# #             "to query the correct table fields."
# #         )
# #         query_sql_database_tool = QuerySQLDataBaseTool(
# #             db=self.db, description=query_sql_database_tool_description
# #         )
# #         query_sql_checker_tool_description = (
# #             "Use this tool to double check if your query is correct before executing "
# #             "it. Always use this tool before executing a query with "
# #             f"{query_sql_database_tool.name}!"
# #         )
# #         query_sql_checker_tool = QuerySQLCheckerTool(
# #             db=self.db, llm=self.llm, description=query_sql_checker_tool_description
# #         )
# #         return [
# #             query_sql_database_tool,
# #             info_sql_database_tool,
# #             list_sql_database_tool,
# #             query_sql_checker_tool,
# #         ]

# # 