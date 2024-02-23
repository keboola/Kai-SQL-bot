import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import dotenv
import langserve
import uvicorn
import yaml
from fastapi import FastAPI
from fastapi.routing import APIRoute
from langchain_community.callbacks import LLMonitorCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_openai import ChatOpenAI
from langserve import CustomUserType
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.routing import Route
from uvicorn.config import LOGGING_CONFIG

import prompts
from agent import AgentBuilder

LOG = logging.getLogger(__package__)
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

    def convert_to_agent_input(self) -> Dict[str, Any]:
        chat_history: List[BaseMessage] = []
        for human, ai in self.chat_history:
            chat_history.append(HumanMessage(content=human))
            chat_history.append(AIMessage(content=ai))
        return {'input': self.input, 'chat_history': chat_history}


def _create_api_chain() -> Runnable:
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
             .build())

    config: Dict[str, Any] = {}
    tracking_id = os.environ.get('LUNARY_APP_ID')
    if tracking_id:
        config['callbacks'] = [LLMonitorCallbackHandler(app_id=tracking_id)]

    def _handle_chain_request(rq: _ChatApiRq) -> Mapping[str, Any]:
        LOG.info(f'Request handler started.')
        start = time.perf_counter()
        try:
            return agent.invoke(input=rq.convert_to_agent_input(), config=config)
        finally:
            duration = time.perf_counter() - start
            LOG.info(f'Request handler finished in {duration:0.02f} seconds.')

    async def _ahandle_chain_request(rq: _ChatApiRq) -> Mapping[str, Any]:
        LOG.info(f'Asycn request handler started.')
        start = time.perf_counter()
        try:
            return await agent.ainvoke(input=rq.convert_to_agent_input(), config=config)
        finally:
            duration = time.perf_counter() - start
            LOG.info(f'Async request handler finished in {duration:0.02f} seconds.')

    chain = RunnableLambda(func=_handle_chain_request, afunc=_ahandle_chain_request)
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
    parser.add_argument('--log-config', type=Path, metavar='PATH',
                        help='The uvicorn logging configuration file.')
    args = parser.parse_args()

    app = create_app(server_path=args.server_path)
    log_config = yaml.safe_load(args.log_config.read_text(encoding='utf-8')) if args.log_config else LOGGING_CONFIG
    uvicorn.run(app, host=args.bind, port=args.port, log_config=log_config)


if __name__ == '__main__':
    main()
