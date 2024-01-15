import streamlit as st
from langchain.agents import AgentExecutor
from langchain.callbacks import FileCallbackHandler
from langchain.memory import StreamlitChatMessageHistory
from langchain_community.callbacks import LLMonitorCallbackHandler
from langchain_community.callbacks import StreamlitCallbackHandler

from prompts import ai_intro


class ChatDisplay:
    """
    Represents a chat display for interacting with an AI agent.

    Args:
        agent_executor (AgentExecutor): An instance of the AgentExecutor class responsible for executing AI agent actions.

    Attributes:
        agent_executor (AgentExecutor): An instance of the AgentExecutor class responsible for executing AI agent actions.

    Methods:
        display_chat(): Displays the chat messages and handles user input.

    """

    def __init__(self, agent_executor: AgentExecutor):
        self.agent_executor = agent_executor
        self.msgs = StreamlitChatMessageHistory(key='sql-bot-message-history-in-streamlit')

    def display_chat(self):
        if len(self.msgs.messages) == 0:
            self.msgs.add_ai_message(ai_intro)
        
        for msg in self.msgs.messages:
            st.chat_message(msg.type).write(msg.content)
        
        if user_input := st.chat_input():
            st.chat_message('user').write(user_input)
            response = self.agent_executor.invoke(
                input={'input': user_input},
                config={'callbacks': [
                    StreamlitCallbackHandler(st.container(), expand_new_thoughts=True),
                    LLMonitorCallbackHandler(app_id=st.secrets.LUNARY_APP_ID),
                    FileCallbackHandler('chat_log.txt'),
                ]}
            )
            st.chat_message('ai').write(response['output'])
