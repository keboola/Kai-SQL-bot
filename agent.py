import enum
from typing import List, Optional, TypeVar

from langchain.agents import AgentExecutor, create_sql_agent, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain.memory import ConversationBufferMemory
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.callbacks import LLMonitorCallbackHandler
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate, SystemMessagePromptTemplate
from langchain_core.prompts.chat import HumanMessagePromptTemplate, MessageLike, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from llama_hub.tools.waii import WaiiToolSpec
from llama_index.tools import FunctionTool

import prompts


class SQLAgentCreator:
    def __init__(self, llm, toolkit, custom_tool_list=None, memory=None):
        """
        Initializes an instance of SQLAgentCreator.

        Args:
            llm (str): The language model to be used by the agent.
            toolkit (str): The toolkit to be used by the agent.
            custom_tool_list (list, optional): A list of custom tools to be used by the agent. Defaults to None.
            memory (str, optional): The memory to be used by the agent. Defaults to None.
        """
        self.llm = llm
        self.toolkit = toolkit
        self.custom_tool_list = custom_tool_list or []
        self.memory = memory

    def create_agent(self):
        """
        Creates and returns an agent executor.

        Returns:
            agent_executor: The created agent executor.
        """
        agent_executor = create_sql_agent(
            llm=self.llm,
            toolkit=self.toolkit,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=50,
            extra_tools=self.custom_tool_list,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            memory=self.memory
        )
        return agent_executor


T = TypeVar('T')


def _check_empty(value: T, *, message: Optional[str] = None) -> T:
    if value is not None and (not isinstance(value, str) or value):
        return value
    else:
        message = message or 'Value is None or empty'
        raise ValueError(message)


class AgentBuilder:
    class Model(enum.Enum):
        GPT_4_TURBO = 'gpt-4-1106-preview'
        GPT_4 = 'gpt-4'
        GPT_35_TURBO = 'gpt-3.5-turbo-16k'

        @staticmethod
        def from_text(text: str) -> Optional['AgentBuilder.Model']:
            for m in AgentBuilder.Model:
                if m.value == text:
                    return m

    class Toolkit(enum.Enum):
        WAII = 'WAII Tools'
        LANGCHAIN = 'Langchain SQL Tools'

        @staticmethod
        def from_text(text: str) -> Optional['AgentBuilder.Toolkit']:
            for m in AgentBuilder.Toolkit:
                if m.value == text:
                    return m

    def __init__(self) -> None:
        # snowflake connection parameters
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._account_identifier: Optional[str] = None
        self._database_name: Optional[str] = None
        self._schema_name: Optional[str] = None
        self._warehouse: Optional[str] = None
        # WAII toolkits parameters
        self._waii_api_key: Optional[str] = None
        # Other
        self._model: AgentBuilder.Model = AgentBuilder.Model.GPT_4
        self._toolkit: AgentBuilder.Toolkit = AgentBuilder.Toolkit.LANGCHAIN
        self._use_external_memory: bool = False
        self._lunary_app_id: Optional[str] = None

    def with_snowflake(
            self, *, username: str, password: Optional[str] = None, account_identifier: str, database_name: str,
            schema_name: str, warehouse: str
    ) -> 'AgentBuilder':
        self._username = _check_empty(username, message='username is empty')
        self._password = password  # can be empty if the DB requires no password
        self._account_identifier = _check_empty(account_identifier, message='account_identifier is empty')
        self._database_name = _check_empty(database_name, message='database_name is empty')
        self._schema_name = _check_empty(schema_name, message='schema_name is empty')
        self._warehouse = _check_empty(warehouse, message='warehouse is empty')
        return self

    def with_waii_api_key(self, waii_api_key: str) -> 'AgentBuilder':
        self._waii_api_key = _check_empty(waii_api_key, message='waii_api_key is empty')
        return self

    def with_waii_tools(self, *, waii_api_key: Optional[str] = None) -> 'AgentBuilder':
        self._toolkit = AgentBuilder.Toolkit.WAII
        if waii_api_key:
            self.with_waii_api_key(waii_api_key)
        return self

    def with_langchain_tools(self) -> 'AgentBuilder':
        self._toolkit = AgentBuilder.Toolkit.LANGCHAIN
        return self

    def with_toolkit(self, toolkit: 'AgentBuilder.Toolkit') -> 'AgentBuilder':
        self._toolkit = _check_empty(toolkit, message='toolkit is None')
        return self

    def with_model(self, model: 'AgentBuilder.Model') -> 'AgentBuilder':
        self._model = _check_empty(model, message='model is None')
        return self

    def use_external_memory(self) -> 'AgentBuilder':
        self._use_external_memory = True
        return self

    def log_to_lunary(self, app_id: str) -> 'AgentBuilder':
        self._lunary_app_id = app_id
        return self

    def build(self) -> AgentExecutor:
        llm = ChatOpenAI(model_name=self._model.value, temperature=0, streaming=True)
        if self._toolkit == AgentBuilder.Toolkit.WAII:
            tools = self._get_waii_tools()
            system_prompt = SystemMessagePromptTemplate(prompt=prompts.kai_gen_sql)
        elif self._toolkit == AgentBuilder.Toolkit.LANGCHAIN:
            tools = self._get_langchain_tools(llm)
            system_prompt = SystemMessagePromptTemplate(prompt=prompts.custom_gen_sql)
        else:
            raise ValueError(f'Unknown toolkit: {self._toolkit}')

        prompt: List[MessageLike] = [
            MessagesPlaceholder(variable_name='chat_history'),
            HumanMessagePromptTemplate(prompt=PromptTemplate(input_variables=['input'], template='{input}')),
            MessagesPlaceholder(variable_name='agent_scratchpad')
        ]

        if self._use_external_memory:
            memory = None  # 'chat_history' key must be present in the input dictionary and contain List[BaseMessage]
        else:
            memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

        callbacks: List[BaseCallbackHandler] = []
        if self._lunary_app_id:
            callbacks.append(LLMonitorCallbackHandler(app_id=self._lunary_app_id))

        return initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            agent_kwargs={
                'system_message': system_prompt,
                'extra_prompt_messages': prompt,
            },
            memory=memory,
            verbose=True,
            callbacks=callbacks,
        )

    def _get_waii_tools(self) -> List[BaseTool]:
        conn_string = (f'snowflake://{self._username}'
                       f'@{self._account_identifier}/{self._database_name}'
                       f'?role={self._username}&warehouse={self._warehouse}')
        waii_tool_spec = WaiiToolSpec(
            url='https://tweakit.waii.ai/api/',
            api_key=self._waii_api_key,
            database_key=conn_string,
            verbose=True
        )
        # convert LlamaIndex tools to Langchain tools
        llama_index_tools: List[FunctionTool] = waii_tool_spec.to_tool_list()
        langchain_tools = [t.to_langchain_tool() for t in llama_index_tools]

        # check that the tool descriptions did not get distorted when converted
        waii_tools_descriptions = [(t.metadata.name, t.metadata.description) for t in llama_index_tools]
        langchain_tools_descriptions = [(t.name, t.description) for t in langchain_tools]
        assert waii_tools_descriptions == langchain_tools_descriptions

        return langchain_tools

    def _get_langchain_tools(self, llm: BaseLanguageModel) -> List[BaseTool]:
        conn_string = (f'snowflake://{self._username}:{self._password}'
                       f'@{self._account_identifier}/{self._database_name}/{self._schema_name}'
                       f'?role={self._username}&warehouse={self._warehouse}')
        return SQLDatabaseToolkit(db=SQLDatabase.from_uri(conn_string), llm=llm).get_tools()
