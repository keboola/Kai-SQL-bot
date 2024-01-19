import streamlit as st
from prompts import ai_intro, custom_gen_sql
from langchain.memory import StreamlitChatMessageHistory, ConversationBufferMemory
from langchain.callbacks import FileCallbackHandler, StreamlitCallbackHandler
#from langchain_community.callbacks import LLMonitorCallbackHandler
#from langchain_community.callbacks import StreamlitCallbackHandler


class ChatDisplay:
    """
    Represents a chat display for interacting with an AI agent.

    Args:
        agent_executor (AgentExecutor): An instance of the AgentExecutor class responsible for executing AI agent actions.
        memory (Memory): An instance of the Memory class representing the memory of the AI agent.

    Attributes:
        agent_executor (AgentExecutor): An instance of the AgentExecutor class responsible for executing AI agent actions.
        memory (Memory): An instance of the Memory class representing the memory of the AI agent.
        msgs (StreamlitChatMessageHistory): An instance of the StreamlitChatMessageHistory class representing the chat message history.

    Methods:
        display_chat(): Displays the chat messages and handles user input.

    """

    def __init__(self, agent_executor, memory):
        self.agent_executor = agent_executor
        self.memory = memory
        self.msgs = StreamlitChatMessageHistory()

    def display_chat(self):
        st_callback = StreamlitCallbackHandler(st.container(), expand_new_thoughts=True)
        #lunary_callback = LLMonitorCallbackHandler(app_id=st.secrets.LUNARY_APP_ID)
        #logfile_handler = FileCallbackHandler("chat_log.txt")

        if len(self.msgs.messages) == 0:
            self.msgs.add_ai_message(ai_intro)
        
        for msg in self.msgs.messages:
            st.chat_message(msg.type).write(msg.content)
        
        if prompt := st.chat_input():
            self.msgs.add_user_message(prompt)
            st.chat_message("user").write(prompt)    
            
            prompt_formatted = custom_gen_sql.format(context=prompt)
            try:
                response = self.agent_executor.invoke({"input": prompt_formatted}, callbacks=[st_callback], memory=self.memory, return_intermediate_steps=True)
            except ValueError as e:
                response = str(e)
                if not response.startswith("Could not parse LLM output: `"):
                    raise e
                response = response.removeprefix("Could not parse LLM output: `").removesuffix("`")
        
            self.msgs.add_ai_message(response["output"])
            st.chat_message("ai").write(response["output"])
            
# Usage
# agent_executor = ... # Initialize your agent executor
# memory = ... # Initialize your memory
# chat_display = ChatDisplay(agent_executor, memory)
# chat_display.display_chat()
