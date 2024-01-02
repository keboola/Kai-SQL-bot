"""Toolkit for interacting with a Snowflake SQL database."""
from typing import List

from langchain_core.language_models import BaseLanguageModel
from langchain_core.pydantic_v1 import Field

from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_community.tools import BaseTool
from src.sql_tools.tools import (
    InfoSnowflakeSQLDatabaseTool,
    ListSnowflakeSQLDatabaseTool,
    QuerySnowflakeSQLCheckerTool,
    QuerySnowflakeSQLDataBaseTool,
)
from src.sql_tools.utilities import SnowflakeSQLDatabase


class SnowflakeSQLDatabaseToolkit(BaseToolkit):
    """Toolkit for interacting with Snowflake SQL databases."""

    db: SnowflakeSQLDatabase = Field(exclude=True)
    llm: BaseLanguageModel = Field(exclude=True)

    @property
    def dialect(self) -> str:
        """Return string representation of Snowflake SQL dialect to use."""
        return self.db.dialect

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    def get_tools(self) -> List[BaseTool]:
        """Get the tools in the toolkit."""
        list_snowflake_sql_database_tool = ListSnowflakeSQLDatabaseTool(db=self.db)
        info_snowflake_sql_database_tool_description = (
            "Input to this tool is a comma-separated list of tables, output is the "
            "schema and sample rows for those tables in Snowflake. "
            "Be sure that the tables actually exist by calling "
            f"{list_snowflake_sql_database_tool.name} first! "
            "Example Input: table1, table2, table3"
        )
        info_snowflake_sql_database_tool = InfoSnowflakeSQLDatabaseTool(
            db=self.db, description=info_snowflake_sql_database_tool_description
        )
        query_snowflake_sql_database_tool_description = (
            "Input to this tool is a detailed and correct SQL query, output is a "
            "result from the Snowflake database. If the query is not correct, an error message "
            "will be returned. If an error is returned, rewrite the query, check the "
            "query, and try again. If you encounter an issue with Unknown column "
            f"'xxxx' in 'field list', use {info_snowflake_sql_database_tool.name} "
            "to query the correct table fields."
        )
        query_snowflake_sql_database_tool = QuerySnowflakeSQLDataBaseTool(
            db=self.db, description=query_snowflake_sql_database_tool_description
        )
        query_snowflake_sql_checker_tool_description = (
            "Use this tool to double check if your query is correct before executing "
            "it in Snowflake. Always use this tool before executing a query with "
            f"{query_snowflake_sql_database_tool.name}!"
        )
        query_snowflake_sql_checker_tool = QuerySnowflakeSQLCheckerTool(
            db=self.db, llm=self.llm, description=query_snowflake_sql_checker_tool_description
        )
        return [
            query_snowflake_sql_database_tool,
            info_snowflake_sql_database_tool,
            list_snowflake_sql_database_tool,
            query_snowflake_sql_checker_tool,
        ]
