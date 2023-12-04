import openai
import re
import streamlit as st
import os
import sqlalchemy
import json
import requests
import pandas as pd

from streamlit_ace import st_ace
from langchain.memory import StreamlitChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory

from langchain.agents import create_sql_agent, AgentExecutor
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.agents.agent_types import AgentType
from langchain.prompts import PromptTemplate

from langchain.callbacks import StreamlitCallbackHandler, HumanApprovalCallbackHandler
st.set_page_config(page_title="Kai SQL Bot", page_icon=":robot_face:")

from src.workspace_connection.workspace_connection import connect_to_snowflake
from prompts import frosty_gen_sql, custom_gen_sql


image_path = os.path.dirname(os.path.abspath(__file__))
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


msgs = StreamlitChatMessageHistory(key="chat_messages")
memory = ConversationBufferMemory(chat_memory=msgs)


model_selection = st.sidebar.selectbox("Choose a model", ['gpt-3.5-turbo-16k', 'gpt-4'], help="Select the model you want to use for the chatbot.")
if model_selection == 'default':
    llm = OpenAI(temperature=0, streaming=True)
else:
    llm = ChatOpenAI(model=model_selection, temperature=0,streaming=True)

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
        max_iterations=50,
        extra_tools=custom_tool_list,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        memory=memory
        #human_callback=HumanApprovalCallbackHandler(),
        #suffix=custom_suffix
    )
    return agent_executor, conn_string


language = st.sidebar.selectbox("Language/Jazyk", ["English", "Czech"], help="Select the language you want to use for the chatbot. Currently, only English and Czech are supported.")

snfl_db = translate("snfl_db", language)   

agent_executor, conn_string = initialize_connection()   

#if language == 'Czech':
#    gen_sql_prompt = cz_prompt_template
#if language == 'English':
#    gen_sql_prompt = en_prompt_template

chat_container = st.container()

with chat_container:
    # Create a dictionary to store feedback counts
    feedback_counts = {"thumbs_up": 0, "thumbs_down": 0}

    # Function to handle user feedback
    def handle_feedback(feedback_type):
        feedback_counts[feedback_type] += 1


    ai_intro = "Hello, I'm Kai, your AI SQL Bot. I'm here to assist you with SQL queries. What can I do for you?"

    if len(msgs.messages) == 0:
        msgs.add_ai_message(ai_intro)

    view_messages = st.sidebar.expander("View the message contents in session state")

    for msg in msgs.messages:
        st.chat_message(msg.type).write(msg.content)

    if prompt := st.chat_input():
        msgs.add_user_message(prompt)
        st.chat_message("user").write(prompt)

        st_callback = StreamlitCallbackHandler(st.container(), expand_new_thoughts=True)
        human_callback = HumanApprovalCallbackHandler()
        prompt_formatted = custom_gen_sql.format(context=prompt)
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
    
           
        def execute_sql():
            sql_matches = re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL)
            for sql in sql_matches:
                try:
                    #connect to snowflake using sqlalchemy engine and execute the sql query
                    engine = sqlalchemy.create_engine(conn_string)
                    df = engine.execute(sql).fetchall()
                    df = pd.DataFrame(df)
                    # Append messages
                    #msgs.add_ai_message(df)
                    # Display messages
                    #with st.container():
                        #with st.chat_message("result"):
                            #st.dataframe(df)
                    st.sidebar.write("Results")
                    st.sidebar.dataframe(df)
                    # Spawn a new Ace editor
                    #with st.sidebar.container():
                    #    content = st_ace()
# 
                    ## Display editor's content as you type
                    #    content
                except Exception as e:
                    st.write(e)
                    st.write(translate("invalid_query", language))
        if re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL):
            st.button(translate("execute_sql", language), on_click=execute_sql)     
        #if st.button(translate("regenerate_response", language)):
        #    with chat_container:
        #        st_callback = StreamlitCallbackHandler(chat_container)
        #        prompt_formatted = gen_sql_prompt.format(context=prompt)
        #        response = agent_executor.run(input=prompt_formatted, callbacks=[st_callback])
        #        sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
        #        st.chat_message("Kai").write(response)
        def clear_chat():
            msgs.clear()
            
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
        #log_data = "User: " + last_user_message["content"] + "\n" + "Kai: " + last_output_message["content"] + "\n" + "feedback: " + feedback + "\n"
        headers = {'Content-Type': 'application/json'}
        with view_messages: """
    Memory initialized with:
    ```python
    msgs = StreamlitChatMessageHistory(key="langchain_messages")
    memory = ConversationBufferMemory(chat_memory=msgs)
    ```

    Contents of `st.session_state.langchain_messages`:
    """
    view_messages.json(st.session_state.chat_messages)
        # check if the url exists in the secrets
        #if "url" in st.secrets:
            #r = requests.post(st.secrets["url"], data=log_data.encode('utf-8'), headers=headers)