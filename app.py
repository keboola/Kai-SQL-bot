import openai
import re
import streamlit as st
import os
import requests
import sqlalchemy
import json
import sqlite3
import csv
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from Kai_SQL_bot.Kai_Agent import create_Kai_Agent

from langchain.agents import create_sql_agent, AgentExecutor, initialize_agent, Tool, AgentType, load_tools, ZeroShotAgent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit, create_python_agent, create_csv_agent
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.tools.python.tool import PythonREPLTool
from langchain import LLMChain, LLMMathChain, SerpAPIWrapper
from langchain_experimental.sql import SQLDatabaseChain



from src.workspace_connection.workspace_connection import connect_to_snowflake, snowflake_connection_user_input

image_path = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="KAI SQL Bot", page_icon=":robot_face:")
st.image(image_path+'/static/keboola_logo.png', width=200)
st.header("Kai SQL Bot Demo ")
# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY

def translate(key, lang="English"):
    # Define the path to the JSON file inside the 'languages' folder
    file_path = os.path.join(image_path+"/languages", f"{lang.lower()}.json")

    with open(file_path, "r") as file:
        translations = json.load(file)
        return translations.get(key, key)  # Return key if translation not found.

language = st.selectbox("Language/Jazyk", ["English", "Czech"]) 

snfl_db = translate("snfl_db", language)   

conn_method = st.selectbox(translate("connection_method", language), [translate("demo_db", language), snfl_db])

if conn_method == snfl_db:
    connect_to_snowflake()
    conn_string = f"snowflake://{st.session_state['user']}:{st.session_state['password']}@{st.session_state['account']}/{st.session_state['database']}/{st.session_state['schema']}?warehouse={st.session_state['warehouse']}&role={st.session_state['user']}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=ChatOpenAI(model='gpt-4-0613', temperature=0), db=db)

else:
    st.write(translate("using_demo_db", language)) 
    account_identifier = st.secrets["account_identifier"]
    user = st.secrets["user"]
    password = st.secrets["password"]
    database_name = st.secrets["database_name"]
    schema_name = st.secrets["schema_name"]
    warehouse_name = st.secrets["warehouse_name"]
    role_name = st.secrets["role_name"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
    db = SQLDatabase.from_uri(conn_string)
    csvFile = "output.csv"
    toolkit = SQLDatabaseToolkit(llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0), db=db)
    llm=ChatOpenAI(model='gpt-4-0613', temperature=0)


#!----------------------------------


    agent_executor = create_Kai_Agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=100,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        extra_tools = tools
        #prefix=custom_prefix,
        #suffix=custom_suffix,
        #format_instructions=custom_format_instructions
        
    )



#!----------------------------------


CZ_GEN_SQL = """
Představte se jako odborník na Snowflake SQL jménem Kai.
Vaším úkolem je poskytovat uživatelům platný a spustitelný SQL dotaz.
Uživatelé budou klást otázky a ke každé otázce s přiloženou tabulkou reagujte poskytnutím odpovědi včetně SQL dotazu.

{context}

Zde jsou 6 klíčových pravidel pro interakci, která musíte dodržovat:
<pravidla>
MUSÍTE využít <tableName> a <columns>, které jsou již poskytnuty jako kontext.

Vygenerovaný SQL kód MUSÍTE uzavřít do značek pro formátování markdownu ve tvaru např.
sql
Copy code
(select 1) union (select 2)
Pokud vám neřeknu, abyste v dotazu nebo otázce hledali omezený počet výsledků, MUSÍTE omezit počet odpovědí na 10.
Text / řetězec musíte vždy uvádět v klauzulích jako fuzzy match, např. ilike %keyword%
Ujistěte se, že generujete pouze jeden kód SQL pro Snowflake, ne více.
Měli byste používat pouze uvedené sloupce tabulky <columns> a uvedenou tabulku <tableName>, NESMÍTE si vymýšlet názvy tabulek.
NEUMISŤUJTE čísla na začátek názvů SQL proměnných.
Poznámka: Ve vygenerovaných SQL dotazech použijte dvojité uvozovky kolem názvů sloupců a tabulek, aby se zachovalo správné psaní názvů. Například:
select "column_name" from "tableName";

Nepřehlédněte, že pro fuzzy match dotazy (zejména pro sloupec variable_name) použijte "ilike %keyword%" a vygenerovaný SQL kód uzavřete do značek pro formátování markdownu ve tvaru např.

sql
Copy code
(select 1) union (select 2)
Každou otázku od uživatele zodpovězte tak, abyste zahrnuli SQL dotaz.

Nyní se pojďme pustit do práce. Představte se stručně, popište své dovednosti a uveďte dostupné metriky ve dvou až třech větách. Poté uveďte 3 otázky (použijte odrážky) jako příklad, na co se může uživatel zeptat, a nezapomeňte na každou otázku odpovědět včetně SQL dotazu."""

ENG_GEN_SQL = """
You will be taking on the role of an AI Snowflake SQL Expert named Kai.
Your objective is to provide users with valid and executable SQL queries.
Users will ask questions, and for each question accompanied by a table, you should respond with an answer including a SQL query.

{context}

Here are 6 critical rules for the interaction that you must follow:
<rules>
you MUST make use of <tableName> and <columns> that are already provided as context.

You MUST wrap the generated SQL code within markdown code formatting tags in this format, e.g.
sql
Copy code
(select 1) union (select 2)
If I do not instruct you to find a limited set of results in the SQL query or question, you MUST limit the number of responses to 10.
Text/string must always be presented in clauses as fuzzy matches, e.g. ilike %keyword%
Ensure that you generate only one SQL code for Snowflake, not multiple.
You should only use the table columns provided in <columns>, and the table provided in <tableName>, you MUST NOT create imaginary table names.
DO NOT start SQL variables with numerals.
Note: In the generated SQL queries, use double quotes around column and table names to ensure proper casing preservation, e.g.
select "column_name" from "tableName";

Do not forget to use "ilike %keyword%" for fuzzy match queries (especially for the variable_name column)
and wrap the generated SQL code with markdown code formatting tags in this format, e.g.

sql
Copy code
(select 1) union (select 2)
For each question from the user, ensure to include a query in your response.

Now, let's get started. Begin by introducing yourself briefly, describing your skills, and listing available metrics in two to three sentences. Then, provide 3 example questions (use bullet points) that a user might ask, and remember to answer each question with an SQL query."""

if language == 'Czech':
    GEN_SQL = CZ_GEN_SQL
if language == 'English':
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

    user_input = st.chat_input(translate("ask_a_question", language))

    if user_input:
        # Add user message to the chat
        with st.chat_message("user"):
            st.markdown(user_input)

        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display "Kai is typing..."
        with st.chat_message("Kai"):
            st.markdown(translate("typing", language))

        st_callback = StreamlitCallbackHandler(st.container())
    #!----------------------------
        output = agent_executor.run(input=GEN_SQL + user_input, callbacks=[st_callback])
    #!----------------------------
 
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
    if last_user_message:  #executes SQL button      
        if st.button(translate("execute_sql", language)):       
            #st.write(sql)
            # Execute the SQL query
             if last_user_message["content"]:
                # uncomment this code if you want to run only the first query
                #sql_match = re.search(r"```sql\n(.*?)\n```", last_output_message["content"], re.DOTALL)    

                #if sql_match:
                #    sql = sql_match.group(1)
                #    st.write(sql) 
                
                # this will find all the queries and run all of them
                sql_matches = re.findall(r"```sql\n(.*?)\n```", last_output_message["content"], re.DOTALL)

                for sql in sql_matches:
                    st.write(sql)    

                    try:
                        #connect to snowflake using sqlalchemy engine and execute the sql query
                        engine = sqlalchemy.create_engine(conn_string)
                        df = engine.execute(sql).fetchall()
                        NateDf = pd.DataFrame(df) #!
                        st.dataframe(df)
                        st.session_state.messages.append({"role": "result", "content": df})
                        st.write(db.run(sql))
                        ##display the results as a dataframe
                        NateDf.to_csv("output.csv", index=False) #!
                        for message in st.session_state.messages:
                            with st.chat_message(message["role"]):
                                if message["role"] == "result":
                                    st.dataframe(message["content"])
                                    

                    except Exception as e:
                        st.write(e)
                        st.write(translate("valid_query", language))

            #log_data = "User: " + user_input + "\n" + "Kai: " + output + "\n"

            #r = requests.post(st.secrets["url"], data=log_data.encode('utf-8'), headers=headers)
#!-------------------------------------       
    if last_user_message:  #executes render button      
        if st.button(translate("Visualize Data", language)):
            agent.run("visualize the data provided in the csv file. Return only one graph that makes the most sense")
            try:
                fig = plt.gcf()
                st.pyplot(fig)
                
            except Exception as e:
                st.write(f"Error excecuting code: {e}")
                st.write("valid_graph")

#!-------------------------------------

    if st.button(translate("regenerate_response", language)):
        st_callback = StreamlitCallbackHandler(st.container())
        output = agent_executor.run(input=GEN_SQL+last_user_message["content"]+"regenerate response", callbacks=[st_callback])
        sql_match = re.search(r"```sql\n(.*)\n```", output, re.DOTALL)
        st.session_state.messages.append({"role": "user", "content": last_user_message["content"]})
        st.session_state.messages.append({"role": "Kai", "content": output})
        with st.chat_message("Kai"):
            st.markdown(output)

    if st.button(translate("clear_chat", language)):
        for key in st.session_state.keys():
            del st.session_state[key]


                
