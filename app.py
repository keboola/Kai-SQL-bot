# Importing libraries
import openai
import re
import streamlit as st
import os
import sqlalchemy
import json
import pandas as pd
from langchain.memory import StreamlitChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from prompts import en_prompt_template, cz_prompt_template

# Setting up the page config
image_path = os.path.dirname(os.path.abspath(__file__)) # Make sure to replace the image with you own
st.set_page_config(page_title="Kai SQL Bot", page_icon=":robot_face:") # Replace with your Title
st.image(image_path+'/static/keboola_logo.png', width=200)
home_title = "Kai SQL Bot"  # Replace with your title
st.markdown(f"""# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>""", unsafe_allow_html=True)

# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY


# Function to switch the app language based on user selection
def translate(key, lang="English"):
    # Define the path to the JSON file inside the 'languages' folder
    file_path = os.path.join(image_path+"/languages", f"{lang.lower()}.json")

    with open(file_path, "r") as file:
        translations = json.load(file)
        return translations.get(key, key)  # Return key if translation not found.

# Initialising & saving the chat history
msgs = StreamlitChatMessageHistory(key="chat_messages")
memory = ConversationBufferMemory(chat_memory=msgs)

# Here you can add other model options in the select box
model_selection = st.sidebar.selectbox("Choose a model", [ 'gpt-4', 'gpt-3.5-turbo-16k'], help="Select the model you want to use for the chatbot.")
llm = ChatOpenAI(model=model_selection, temperature=0, streaming=True)

# The connection to keboola workspace
def initialize_connection():
    account_identifier = st.secrets["account_identifier"]
    user = st.secrets["user"]
    password = st.secrets["password"]
    database_name = st.secrets["database_name"]
    schema_name = st.secrets["schema_name"]
    warehouse_name = st.secrets["warehouse_name"]
    role_name = st.secrets["user"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"
    db = SQLDatabase.from_uri(conn_string)
    toolkit = SQLDatabaseToolkit(llm=llm, db=db)
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=20,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory
    )
    return agent_executor, conn_string

# Dropdown for language selection. Currently supports only English & Czech
language = st.sidebar.selectbox("Language/Jazyk", ["English", "Czech"], help="Select the language you want to use for the chatbot. Currently, only English and Czech are supported.")

snfl_db = translate("snfl_db", language)   

# Intiializing connection variables
agent_executor, conn_string = initialize_connection()   

if language == "Czech":
    gen_sql_prompt = cz_prompt_template
if language == "English":
    gen_sql_prompt = en_prompt_template

chat_container = st.container()

with chat_container:
    # Create a dictionary to store feedback counts
    feedback_counts = {"thumbs_up": 0, "thumbs_down": 0}

    # Function to handle user feedback
    def handle_feedback(feedback_type):
        feedback_counts[feedback_type] += 1


    ai_intro = translate("ai_intro", language)   

    
    if len(msgs.messages) == 0:
        msgs.add_ai_message(ai_intro)

    for msg in msgs.messages:
        st.chat_message(msg.type).write(msg.content)

    if prompt := st.chat_input():
        msgs.add_user_message(prompt)
        st.chat_message("user").write(prompt)

        st_callback = StreamlitCallbackHandler(st.container(), expand_new_thoughts=True)
        prompt_formatted = gen_sql_prompt.format(context=prompt)
        try:
            response = agent_executor.run(input=prompt_formatted, callbacks=[st_callback], memory=memory)
        except ValueError as e:
            response = str(e)
            if not response.startswith("Could not parse LLM output: `"):
                raise e
            response = response.removeprefix("Could not parse LLM output: `").removesuffix("`")

        msgs.add_ai_message(response)
        st.chat_message("Kai").write(response)


with st.container():
    # get the output of the last message from the agent 
    if len(msgs.messages) > 1:
        last_output_message = msgs.messages[-1].content    
    
        # Function to execute SQL queries button in case of a query in the response   
        def execute_sql():
            sql_matches = re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL)
            for sql in sql_matches:
                try:
                    #connect to snowflake using sqlalchemy engine and execute the sql query
                    engine = sqlalchemy.create_engine(conn_string)
                    df = engine.execute(sql).fetchall()
                    df = pd.DataFrame(df)
                    st.sidebar.write("Results")
                    st.sidebar.dataframe(df)
                except Exception as e:
                    st.write(e)
                    st.write(translate("invalid_query", language))
        if re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL):
            st.button(translate("execute_sql", language), on_click=execute_sql)  
        # if st.button(translate("regenerate_response", language)):
        #     last_user_message = msgs.messages[-2].content
        #     st_callback = StreamlitCallbackHandler(st.container())
        #     regenerate_prompt_formatted = gen_sql_prompt.format(context=last_user_message)
        #     response = agent_executor.run(input=regenerate_prompt_formatted, callbacks=[st_callback], memory=memory)
        #     sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
        #     msgs.add_ai_message(response)
        #     st.chat_message("Kai").write(response)

        # Function to clear the chat
        def clear_chat():
            msgs.clear()
            
        st.sidebar.button(translate("clear_chat", language), on_click=clear_chat)

        # Feedback button
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

