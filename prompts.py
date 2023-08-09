import streamlit as st

QUALIFIED_TABLE_NAME = "seznam_pobocek"
TABLE_DESCRIPTION = """
Table has data regarding cities, branches, new branches etc
"""

GEN_SQL = """
You will be acting as an AI Snowflake SQL Expert named Kai.
Your goal is to give correct, executable sql query to users.
The user will ask questions, for each question you should respond and include a sql query based on the question and the table. 

{context}

Here are 6 critical rules for the interaction you must abide:
<rules>
you MUST MUST make use of <tableName> and <columns> are already provided in the context for you.
1. You MUST MUST wrap the generated sql code within ``` sql code markdown in this format e.g
```sql
(select 1) union (select 2)
```
2. If I don't tell you to find a limited set of results in the sql query or question, you MUST limit the number of responses to 10.
3. Text / string where clauses must be fuzzy match e.g ilike %keyword%
4. Make sure to generate a single snowflake sql code, not multiple. 
5. You should only use the table columns given in <columns>, and the table given in <tableName>, you MUST NOT hallucinate about the table names
6. DO NOT put numerical at the very front of sql variable.
</rules>

Don't forget to use "ilike %keyword%" for fuzzy match queries (especially for variable_name column)
and wrap the generated sql code with ``` sql code markdown in this format e.g:
```sql
(select 1) union (select 2)
```

For each question from the user, make sure to include a query in your response.

Now to get started, please briefly introduce yourself, describe the  at a high level, and share the available metrics in 2-3 sentences.
Then provide 3 example questions using bullet points.
"""

@st.cache_data(show_spinner=False)
def get_table_context(table_name: str, table_description: str, metadata_query: str = None):
    conn = st.experimental_connection("snowpark")
    columns = conn.query(f"""
        SELECT COLUMN_NAME, DATA_TYPE FROM KEBOOLA_16017.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'in.c-data' AND TABLE_NAME = '{QUALIFIED_TABLE_NAME}'
        """,
    )
    columns = "\n".join(
        [
            f"- **{columns['COLUMN_NAME'][i]}**: {columns['DATA_TYPE'][i]}"
            for i in range(len(columns["COLUMN_NAME"]))
        ]
    )
    context = f"""
Here is the table name <tableName> {"seznam_pobocek"} </tableName>

<tableDescription>{table_description}</tableDescription>

Here are the columns of the {(QUALIFIED_TABLE_NAME)}

<columns>\n\n{columns}\n\n</columns>
    """
    if metadata_query:
        st.write(metadata_query)
        metadata = conn.query(metadata_query)
        metadata = "\n".join(
            [
                f"- **{metadata['VARIABLE_NAME'][i]}**: {metadata['DEFINITION'][i]}"
                for i in range(len(metadata["VARIABLE_NAME"]))
            ]
        )
        context = context + f"\n\nAvailable variables by VARIABLE_NAME:\n\n{metadata}"
    return context

def get_system_prompt():
    table_context = get_table_context(
        table_name=QUALIFIED_TABLE_NAME,
        table_description=TABLE_DESCRIPTION    )
    return GEN_SQL.format(context=table_context)


# do `streamlit run prompts.py` to view the initial system prompt in a Streamlit app
if __name__ == "__main__":
    st.header("System prompt for KAI")
    st.markdown(get_system_prompt())
