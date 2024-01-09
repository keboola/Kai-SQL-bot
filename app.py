import openai
import re
import streamlit as st
import os
import sqlalchemy
import json
import pandas as pd

from langchain.chat_models import ChatOpenAI
from langchain.memory import StreamlitChatMessageHistory, ConversationBufferMemory

from src.database_connection.database_connection import DatabaseConnection
from agent import SQLAgentCreator
from chat import ChatDisplay
from few_shot_examples import custom_tool_list

image_path = os.path.dirname(os.path.abspath(__file__))
st.image(image_path+'/static/keboola_logo.png', width=200)
home_title = "Kai SQL Bot"  # Replace with your title
st.markdown(f"""# {home_title} <span style="color:#2E9BF5; font-size:16px;">Beta</span>""", unsafe_allow_html=True)
# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY

model_selection = st.sidebar.selectbox("Choose a model", ['gpt-4-1106-preview', 'gpt-4', 'gpt-3.5-turbo-16k'], help="Select the model you want to use for the chatbot.")
llm = ChatOpenAI(model=model_selection, temperature=0,streaming=True)

db_conn = DatabaseConnection(st.secrets["account_identifier"], st.secrets["user"], st.secrets["password"],
                                    st.secrets["database_name"], st.secrets["schema_name"], st.secrets["warehouse_name"], st.secrets["user"])

toolkit = db_conn.create_toolkit(llm)

msgs = StreamlitChatMessageHistory(key="messages")
memory = ConversationBufferMemory(chat_memory=msgs)

agent_creator = SQLAgentCreator(toolkit=toolkit, llm=llm, custom_tool_list=custom_tool_list, memory=memory)
agent_executor = agent_creator.create_agent()

# Create a dictionary to store feedback counts
feedback_counts = {"thumbs_up": 0, "thumbs_down": 0}

# Function to handle user feedback
def handle_feedback(feedback_type):
    feedback_counts[feedback_type] += 1


chat_display = ChatDisplay(agent_executor, memory)
chat_display.display_chat()

view_messages = st.sidebar.expander("View the message contents in session state")


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
                st.sidebar.write("Results")
                st.sidebar.dataframe(df)
            except Exception as e:
                st.write(e)
                st.write("invalid_query")
    if re.findall(r"```sql\n(.*?)\n```", last_output_message, re.DOTALL):
        st.button("execute_sql", on_click=execute_sql)     

    def clear_chat():
        msgs.clear()
        
    st.sidebar.button("clear_chat", on_click=clear_chat)
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
view_messages.json(st.session_state.messages)
