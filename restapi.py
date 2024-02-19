import argparse
import os
from typing import Any, List, Mapping, Optional, Tuple

import dotenv
import langserve
import uvicorn
from fastapi import FastAPI
from fastapi.routing import APIRoute
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langserve import CustomUserType
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route

import prompts
from agent import AgentBuilder


_API_VERSION = 'v1'
_LLM = AgentBuilder.Model.GPT_4


async def _redirect_root_to_docs(rq: Request) -> Response:
    return RedirectResponse(f'{rq.scope.get("root_path")}/docs')


class _MessageApiResp(BaseModel):
    message: str


async def _get_status(_rq: Request) -> _MessageApiResp:
    """Gets the REST API server status."""
    return _MessageApiResp(message='SQL-Bot API server - ready.')


class _ChatApiRq(CustomUserType):
    """Describes the API request."""
    chat_history: List[Tuple[str, str]] = Field(examples=[[('human question', 'ai response')]])
    input: str

    def convert_to_agent_input(self) -> Mapping[str, Any]:
        chat_history: List[BaseMessage] = []
        for human, ai in self.chat_history:
            chat_history.append(HumanMessage(content=human))
            chat_history.append(AIMessage(content=ai))
        return {'input': self.input, 'chat_history': chat_history}


def _create_api_chain():
    """Creates chain that converts the API request into the agents input dict and runs the agent."""
    agent = (AgentBuilder()
             .with_model(_LLM)
             .with_waii_tools(waii_api_key=os.environ['WAII_API_KEY'])
             .with_snowflake(
                username=os.environ['SNFLK_USER'], password=os.environ['SNFLK_PASSWORD'],
                account_identifier=os.environ['SNFLK_ACCOUNT_IDENTIFIER'], database_name=os.environ['SNFLK_DATABASE'],
                schema_name=os.environ['SNFLK_SCHEMA'], warehouse=os.environ['SNFLK_WAREHOUSE']
             )
             .use_external_memory()
             .log_to_lunary(app_id=os.environ.get('LUNARY_APP_ID'))
             .build())
    chain = RunnableLambda(_ChatApiRq.convert_to_agent_input) | agent
    chain = chain.with_types(input_type=_ChatApiRq)
    return chain


class _TrConfigRq(BaseModel):
    chat_history: List[Tuple[str, str]] = Field(examples=[[('human question', 'ai response')]])


class _TrConfigResp(BaseModel):
    transformation_name: str = Field(description='name of the transformation (with spaces between words)')
    transformation_description: str = Field(description='description of the transformation')
    output_table: str = Field(description='name of the output table')


def _get_tr_config_handler():
    llm = ChatOpenAI(model_name=_LLM.value, temperature=0)
    parser = JsonOutputParser(pydantic_object=_TrConfigResp)
    chain = prompts.tr_config_prompt | llm | parser

    async def _get_tr_config(rq: _TrConfigRq) -> _TrConfigResp:
        chat_history: List[BaseMessage] = []
        # take up to 2
        for human, ai in rq.chat_history[-2:]:
            chat_history.append(HumanMessage(content=human))
            chat_history.append(AIMessage(content=ai))
        return await chain.ainvoke({
            'format_instructions': parser.get_format_instructions(),
            'chat_history': chat_history,
        })

    return _get_tr_config


def create_app(*, server_path: Optional[str] = None) -> FastAPI:
    dotenv.load_dotenv()
    server_path = server_path or os.getenv('SERVER_PATH')
    app = FastAPI(
        title='SQL-Bot REST API',
        routes=[
            Route('/', endpoint=_redirect_root_to_docs),
            APIRoute('/status', methods=['GET'], endpoint=_get_status),
            APIRoute(f'/{_API_VERSION}/tr_config', methods=['POST'], endpoint=_get_tr_config_handler()),
        ],
        root_path=server_path,
    )
    langserve.add_routes(
        app,
        runnable=_create_api_chain(),
        enabled_endpoints=['invoke', 'stream'],
        path=f'/{_API_VERSION}/agent',
    )
    return app


def main():
    parser = argparse.ArgumentParser(description='Starts REST API server for SQL-Bot.')
    parser.add_argument('--bind', default='localhost',
                        help='Name or IP address of the network interface where the sever will listen.')
    parser.add_argument('--port', type=int, default=5000, help='The port to listen at.')
    parser.add_argument('--server-path', help='The URL path prefix where this API is available.')
    args = parser.parse_args()

    app = create_app(server_path=args.server_path)
    uvicorn.run(app, host=args.bind, port=args.port)


if __name__ == '__main__':
    main()
