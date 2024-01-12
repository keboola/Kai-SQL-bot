"""SQLAlchemy wrapper specifically tailored for Snowflake databases."""

from typing import Any, List, Optional, Union
from sqlalchemy import create_engine, MetaData, inspect, select, Table
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

class SnowflakeSQLDatabase:
    """SQLAlchemy wrapper specifically tailored for Snowflake databases."""

    def __init__(
        self,
        engine: Engine,
        schema: Optional[str] = None,
        metadata: Optional[MetaData] = None,
        ignore_tables: Optional[List[str]] = None,
        include_tables: Optional[List[str]] = None,
        sample_rows_in_table_info: int = 3,
        indexes_in_table_info: bool = False,
        max_string_length: int = 300,
    ):
        """Initialize the Snowflake database connection."""
        self._engine = engine
        self._schema = schema
        self._metadata = metadata or MetaData()

        self._inspector = inspect(self._engine)
        self._all_tables = set(self._inspector.get_table_names(schema=schema))
        self._include_tables = set(include_tables) if include_tables else set()
        self._ignore_tables = set(ignore_tables) if ignore_tables else set()

        self._sample_rows_in_table_info = sample_rows_in_table_info
        self._indexes_in_table_info = indexes_in_table_info
        self._max_string_length = max_string_length

        self._metadata.reflect(bind=self._engine, only=list(self.get_usable_table_names()), schema=self._schema)

    @classmethod
    def from_snowflake_conn(
        cls,
        user: str,
        password: str,
        account: str,
        warehouse: str,
        database: str,
        schema: str,
        role: Optional[str] = None,
        engine_args: Optional[dict] = None,
        **kwargs: Any
    ):
        """Create a SnowflakeSQLDatabase instance from Snowflake connection details."""
        connection_string = (
            f"snowflake://{user}:{password}@{account}/{database}/{schema}"
            f"?warehouse={warehouse}"
        )
        if role:
            connection_string += f"&role={role}"
        
        engine = create_engine(connection_string, **(engine_args or {}))
        return cls(engine, schema=schema, **kwargs)

    def get_usable_table_names(self) -> List[str]:
        """Get names of tables available, excluding ignored tables and including only included tables."""
        if self._include_tables:
            return sorted(self._include_tables)
        return sorted(self._all_tables - self._ignore_tables)

    def _execute(
        self,
        command: str,
        fetch: Union['all', 'one'] = 'all',
    ) -> List[dict]:
        """Executes SQL command through underlying engine."""
        with self._engine.connect() as connection:
            cursor = connection.execute(text(command))
            if fetch == 'all':
                result = [dict(row) for row in cursor.fetchall()]
            elif fetch == 'one':
                result = [dict(cursor.fetchone())]
            else:
                raise ValueError("Invalid fetch type. Use 'all' or 'one'.")
        return result

    def run(
        self,
        command: str,
        fetch: Union['all', 'one'] = 'all',
    ) -> str:
        """Execute a Snowflake SQL command and return a string representing the results."""
        try:
            result = self._execute(command, fetch)
            return str(result)
        except SQLAlchemyError as e:
            return f"Error: {e}"

    def get_table_info(self, table_names: Optional[List[str]] = None) -> str:
        """Get information about specified tables."""
        all_table_names = self.get_usable_table_names()
        if table_names:
            missing_tables = set(table_names) - set(all_table_names)
            if missing_tables:
                raise ValueError(f"Tables not found: {missing_tables}")
            all_table_names = table_names

        tables_info = []
        for table_name in all_table_names:
            table = Table(table_name, self._metadata, autoload_with=self._engine)
            table_info = str(table)
            if self._indexes_in_table_info or self._sample_rows_in_table_info:
                table_info += "\n/*"
                if self._indexes_in_table_info:
                    indexes = self._inspector.get_indexes(table_name)
                    index_info = "\n".join(f"Index: {index['name']}" for index in indexes)
                    table_info += f"\n{index_info}\n"
                if self._sample_rows_in_table_info:
                    sample_rows = self._execute(f"SELECT * FROM {table_name} LIMIT {self._sample_rows_in_table_info}", 'all')
                    table_info += f"\nSample Rows:\n{sample_rows}\n"
                table_info += "*/"
            tables_info.append(table_info)

        return "\n\n".join(tables_info)

# Additional utility methods and customizations for Snowflake can be added here.

