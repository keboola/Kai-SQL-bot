import openai
import re
import streamlit as st
import os
import sqlalchemy
import json
import requests

from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler

from src.workspace_connection.workspace_connection import connect_to_snowflake


image_path = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="Kai SQL Bot", page_icon=":robot_face:")
st.image(image_path+'/static/keboola_logo.png', width=200)
home_title = "Kai SQL Bot"  # Replace with your title

# Display the title with the "Beta" label using HTML styling
st.markdown(f"""# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>""", unsafe_allow_html=True)
# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY

def translate(key, lang="English"):
    # Define the path to the JSON file inside the 'languages' folder
    file_path = os.path.join(image_path+"/languages", f"{lang.lower()}.json")

    with open(file_path, "r") as file:
        translations = json.load(file)
        return translations.get(key, key)  # Return key if translation not found.


def initialize_demo_connection():
    account_identifier = st.secrets["account_identifier"]
    user = st.secrets["user"]
    password = st.secrets["password"]
    database_name = st.secrets["database_name"]
    schema_name = st.secrets["schema_name"]
    warehouse_name = st.secrets["warehouse_name"]
    role_name = st.secrets["user"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0), db=db)
    agent_executor = create_sql_agent(
        llm=ChatOpenAI(model='gpt-3.5-turbo-16k', temperature=0),
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=100,
        agent_type=AgentType.OPENAI_FUNCTIONS
        #prefix=custom_prefix,
        #suffix=custom_suffix,
        #format_instructions=custom_format_instructions
    )
    return agent_executor, conn_string


language = st.sidebar.selectbox("Language/Jazyk", ["English", "Czech"], help="Select the language you want to use for the chatbot. Currently, only English and Czech are supported.")


snfl_db = translate("snfl_db", language)   

#conn_method = st.sidebar.selectbox(translate("connection_method", language), [translate("demo_db", language), snfl_db], help="Select the connection method you want to use for the chatbot. Currently, only Snowflake is supported.")

#if conn_method == snfl_db : 
#    agent_executor,conn_string = initialize_snowflake_connection()
    

agent_executor, conn_string = initialize_demo_connection()   

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

Remember to answer each question with an SQL query"""

if language == 'Czech':
    GEN_SQL = CZ_GEN_SQL
if language == 'English':
    GEN_SQL = ENG_GEN_SQL  
    
if "messages" not in st.session_state:
    st.session_state.messages = []
    ai_intro = "Hello, I'm Kai, your AI SQL Bot. I'm here to assist you with SQL queries.What can I do for you?"
    
    st.session_state.messages.append({"role":"Kai", "content" : ai_intro})

# Display chat messages from history
with st.container():
    # Create a dictionary to store feedback counts
    feedback_counts = {"thumbs_up": 0, "thumbs_down": 0}

    # Function to handle user feedback
    def handle_feedback(feedback_type):
        feedback_counts[feedback_type] += 1

    if st.session_state.messages:
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
        def execute_sql():
             if last_user_message["content"]:
                sql_matches = re.findall(r"```sql\n(.*?)\n```", last_output_message["content"], re.DOTALL)
                for sql in sql_matches:
                    try:
                        #connect to snowflake using sqlalchemy engine and execute the sql query
                        engine = sqlalchemy.create_engine(conn_string)
                        df = engine.execute(sql).fetchall()
                        # Append messages
                        st.session_state.messages.append({"role": "result", "content": df})
                
                    except Exception as e:
                        st.write(e)
                        st.write(translate("invalid_query", language))
        
        st.button(translate("execute_sql", language), on_click=execute_sql)     
        
            

        if st.button(translate("regenerate_response", language)):
            st_callback = StreamlitCallbackHandler(st.container())
            output = agent_executor.run(input=GEN_SQL+last_user_message["content"]+"regenerate response", callbacks=[st_callback])
            sql_match = re.search(r"```sql\n(.*)\n```", output, re.DOTALL)
            st.session_state.messages.append({"role": "user", "content": last_user_message["content"]})
            st.session_state.messages.append({"role": "Kai", "content": output})
            with st.chat_message("Kai"):
                st.markdown(output)
        def clear_chat():
            st.session_state.messages = []
            last_result_message = None
            last_output_message = None
            
        st.sidebar.button(translate("clear_chat", language), on_click=clear_chat)
        # Create two columns with custom widths
        col_1, col_2 = st.columns([1, 5])
        # Apply custom CSS to reduce margin between columns
        st.markdown(
            """
            <style>
            .st-b3 {
                margin-left: -10px; /* Adjust the negative margin as needed */
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # Display thumbs-up button in the first column
        with col_1:
            if st.button("👍"):
                handle_feedback("thumbs_up")
        # Display thumbs-down button in the second column
        with col_2:
            if st.button("👎"):
                handle_feedback("thumbs_down")
        if feedback_counts["thumbs_up"] > feedback_counts["thumbs_down"]:
            feedback = "positive"
        elif feedback_counts["thumbs_up"] < feedback_counts["thumbs_down"]:
            feedback = "negative"
        else:
            # If both counts are equal or both are 0, set a default feedback
            feedback = "neutral"
        log_data = "User: " + last_user_message["content"] + "\n" + "Kai: " + last_output_message["content"] + "\n" + "feedback: " + feedback + "\n"
        headers = {'Content-Type': 'application/json'}

        # check if the url exists in the secrets
        if "url" in st.secrets:
            r = requests.post(st.secrets["url"], data=log_data.encode('utf-8'), headers=headers)