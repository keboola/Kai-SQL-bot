import openai
import re
import streamlit as st
import os
import requests
import sqlalchemy

from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler


from src.workspace_connection.workspace_connection import connect_to_snowflake, snowflake_connection_user_input

image_path = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="KAI SQL Bot", page_icon=":robot_face:")
st.image(image_path+'/static/keboola_logo.png', width=200)
st.header("Kai SQL Bot Demo ")
# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY

conn_method = st.selectbox("Connection Method", ["Demo Database", "Snowflake Database Connection"])

if conn_method == "Snowflake Database Connection":
    connect_to_snowflake()
    conn_string = f"snowflake://{st.session_state['user']}:{st.session_state['password']}@{st.session_state['account']}/{st.session_state['database']}/{st.session_state['schema']}?warehouse={st.session_state['warehouse']}&role={st.session_state['user']}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=ChatOpenAI(model='gpt-4-0613', temperature=0), db=db)

else:
    st.write("Using Demo Database") 
    account_identifier = st.secrets["account_identifier"]
    user = st.secrets["user"]
    password = st.secrets["password"]
    database_name = st.secrets["database_name"]
    schema_name = st.secrets["schema_name"]
    warehouse_name = st.secrets["warehouse_name"]
    role_name = st.secrets["role_name"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0), db=db)

option = st.selectbox(
    'Language Selection',
    ('Czech', 'English'))

  

agent_executor = create_sql_agent(
    llm=ChatOpenAI(model='gpt-4-0613', temperature=0),
    toolkit=toolkit,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=100,
    agent_type=AgentType.OPENAI_FUNCTIONS
    #prefix=custom_prefix,
    #suffix=custom_suffix,
    #format_instructions=custom_format_instructions
)


CZ_GEN_SQL = """
Vžijte se do role AI odborníka na Snowflake SQL jménem Kai.
Vaším cílem je poskytnout uživatelům validní a spustitelný SQL dotaz.
Uživatelé budou klást otázky. Na každou otázku s přiloženou tabulkou reagujte poskytnutím odpovědi včetně SQL dotazu.
{context}

Zde je 6 kritických pravidel pro interakci, která musíte dodržovat:
<pravidla>
MUSÍTE využít <tableName> a <columns>, které byla předána jako kontext výše.
1. MUSÍTE zabalit vygenerovaný sql kód do markdownu v tomto formátu např
```sql
(select 1) union (select 2)
```
2. Pokud vám neřeknu, abyste v dotazu nebo otázce sql našli omezenou sadu výsledků, MUSÍTE omezit počet odpovědí na 10.
3. Text / string musíte vždy uvádět v klauzulích jako fuzzy match, např ilike %keyword%
4. Ujistěte se, že vygenerujete jeden snowflake sql code, né více.
5. Měli byste používat pouze uvedené sloupce tabulky <columns>, a uvedenou tabulků <tableName>, NESMÍTE halucinovat ohledně názvů tabulek
6. NEUMÍSŤUJTE číslice na začátku sql proměnných.
</pravidla>
Nezapomeňte použít "ilike %keyword%" pro dotazy na fuzzy match (zejména pro sloupec variable_name)
a zabalte vygenerovaný sql kód do markdownu v tomto formátu např.
```sql
(select 1) union (select 2)

Ve vygenerovaných SQL dotazech obalte  názvy sloupců a tabulek do dvojitých uvozovek, kdykoli je to možné, např.
select "column_name" from "tableName";
```
U každé otázky od uživatele nezapomeňte do odpovědi zahrnout SQL dotaz.
Odpověď pište v českém jazyce.
Nyní se pro začátek představte, popište zevrubně svoje schopnosti a vypište dostupné metriky ve dvou až třech větách. Poté vypište 3 otázky (použijte odrážky) jako příklad, na co se může uživatel zeptat (a nezapomeňte odpovědět česky)."""

ENG_GEN_SQL = """
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

Note: In the generated SQL queries, wrap column names and table names with double quotes whereever applicable, e.g.,
select "column_name" from "tableName";

Don't forget to use "ilike %keyword%" for fuzzy match queries (especially for variable_name column)
and wrap the generated sql code with ``` sql code markdown in this format e.g:
```sql
(select 1) union (select 2)
```

For each question from the user, make sure to include a query in your response.

Now to get started, answer the following question: 

"""

if option == 'Czech':
    GEN_SQL = CZ_GEN_SQL
if option == 'English':
    GEN_SQL = ENG_GEN_SQL  
    
# Initialize chat history

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
with st.container():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Ask a question")

    if user_input:
        # Add user message to the chat
        with st.chat_message("user"):
            st.markdown(user_input)

        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display "Kai is typing..."
        with st.chat_message("Kai"):
            st.markdown("Kai is typing...")

        st_callback = StreamlitCallbackHandler(st.container())
        output = agent_executor.run(input=GEN_SQL + user_input, callbacks=[st_callback])
        
        # Add Kai's message to session state
        st.session_state.messages.append({"role": "Kai", "content": output})

        # Display Kai's message
        with st.chat_message("Kai"):
            st.markdown(output)

with st.container():    
    last_output_message = []
    last_user_message = []
    for message in reversed(st.session_state.messages):
        if message["role"] == "Kai":
            last_output_message = message
            break
    for message in reversed(st.session_state.messages):
        if message["role"] =="user":
            last_user_message = message
            break  
    if last_user_message:        
        if st.button("Execute SQL"):       
            #st.write(sql)
            # Execute the SQL query
             if last_user_message["content"]:
                 # uncomment this code if you want to run only the first query
                """sql_match = re.search(r"```sql\n(.*?)\n```", last_output_message["content"], re.DOTALL)    

                if sql_match:
                    sql = sql_match.group(1)
                    st.write(sql) """
                # this will find all the queries and run all of them
                sql_matches = re.findall(r"```sql\n(.*?)\n```", last_output_message["content"], re.DOTALL)

                for sql in sql_matches:
                    st.write(sql)    

                    try:
                        #connect to snowflake using sqlalchemy engine and execute the sql query
                        engine = sqlalchemy.create_engine(conn_string)
                        df = engine.execute(sql).fetchall()
                        st.dataframe(df)
                        st.session_state.messages.append({"role": "result", "content": df})
                        st.write(db.run(sql))
                        ##display the results as a dataframe
                        for message in st.session_state.messages:
                            with st.chat_message(message["role"]):
                                if message["role"] == "result":
                                    st.dataframe(message["content"])

                    except Exception as e:
                        st.write(e)
                        st.write("Please make sure your SQL query is valid")

            #log_data = "User: " + user_input + "\n" + "Kai: " + output + "\n"

            #r = requests.post(st.secrets["url"], data=log_data.encode('utf-8'), headers=headers)

        if st.button("Regenerate Response"):
            st_callback = StreamlitCallbackHandler(st.container())
            output = agent_executor.run(input=GEN_SQL+last_user_message["content"]+"regenerate response", callbacks=[st_callback])
            sql_match = re.search(r"```sql\n(.*)\n```", output, re.DOTALL)
            st.session_state.messages.append({"role": "user", "content": last_user_message["content"]})
            st.session_state.messages.append({"role": "Kai", "content": output})
            with st.chat_message("Kai"):
                st.markdown(output)

        if st.button("Clear chat"):
            for key in st.session_state.keys():
                del st.session_state[key]


                