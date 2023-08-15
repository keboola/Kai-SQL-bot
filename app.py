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

# Initialize chat history

if "messages" not in st.session_state:
    st.session_state.messages = []
# Display chat messages from history on app rerun



with st.container():
    def get_text():
        input_text = st.chat_input("Ask a question")
        return input_text

    headers = {'Content-Type': 'application/json'}
    user_input = get_text()


    if user_input:
        initial_input = {"role": "user", "content": user_input}
        st.session_state.messages.append(initial_input)
    #with st.chat_message(initial_input["role"]):
    #    st.markdown(initial_input["content"])

        with st.chat_message("Kai"):
            st.markdown("Kai is typing...")
            st_callback = StreamlitCallbackHandler(st.container())

        output = agent_executor.run(input=GEN_SQL+user_input, callbacks=[st_callback])
        st.session_state.messages.append({"role": "Kai", "content": output})


    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

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
                sql_match = re.search(r"```sql\n(.*)\n```", last_output_message["content"], re.DOTALL)    

                if sql_match:
                    sql = sql_match.group(1)
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


                