import streamlit as st
from prompts import ai_intro, custom_gen_sql
from langchain.memory import StreamlitChatMessageHistory, ConversationBufferMemory
from langchain.callbacks import StreamlitCallbackHandler, LLMonitorCallbackHandler, FileCallbackHandler


def display_chat(msgs, memory, agent_executor):
    st_callback = StreamlitCallbackHandler(st.container(), expand_new_thoughts=True)
    lunary_callback = LLMonitorCallbackHandler(app_id=st.secrets.LUNARY_APP_ID)
    logfile_handler = FileCallbackHandler("chat_log.txt")
    if len(msgs.messages) == 0:
        msgs.add_ai_message(ai_intro)
    
    for msg in msgs.messages:
        st.chat_message(msg.type).write(msg.content)
    
    if prompt := st.chat_input():
        msgs.add_user_message(prompt)
        st.chat_message("user").write(prompt)    
    
        prompt_formatted = custom_gen_sql.format(context=prompt)
        try:
            response = agent_executor.run(input=prompt_formatted, callbacks=[st_callback, lunary_callback, logfile_handler], memory=memory, return_intermediate_steps=True )
        except ValueError as e:
            response = str(e)
            if not response.startswith("Could not parse LLM output: `"):
                raise e
            response = response.removeprefix("Could not parse LLM output: `").removesuffix("`")
    
        msgs.add_ai_message(response)
        st.chat_message("Kai").write(response)

# get the output of the last message from the agent 


if __name__ == '__main__':
    display_chat()