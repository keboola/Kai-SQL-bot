import argparse
import os
from typing import Any, List, Mapping, Tuple

import dotenv
import langserve
import uvicorn
from fastapi import FastAPI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from langserve import CustomUserType
from pydantic import Field
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.routing import Route

from agent import AgentBuilder


async def _redirect_root_to_docs(_rq: Request):
    return RedirectResponse('/docs')


class _ApiRequest(CustomUserType):
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
             .with_model(AgentBuilder.Model.GPT_4)
             .with_waii_tools(waii_api_key=os.environ['WAII_API_KEY'])
             .with_snowflake(
                username=os.environ['SNFLK_USER'], password=os.environ['SNFLK_PASSWORD'],
                account_identifier=os.environ['SNFLK_ACCOUNT_IDENTIFIER'], database_name=os.environ['SNFLK_DATABASE'],
                schema_name=os.environ['SNFLK_SCHEMA'], warehouse=os.environ['SNFLK_WAREHOUSE']
             )
             .use_external_memory()
             .log_to_lunary(app_id=os.environ.get('LUNARY_APP_ID'))
             .build())
    chain = RunnableLambda(_ApiRequest.convert_to_agent_input) | agent
    chain = chain.with_types(input_type=_ApiRequest)
    return chain


def main():
    parser = argparse.ArgumentParser(description='Starts REST API server for SQL-Bot.')
    parser.add_argument('--bind', default='localhost',
                        help='Name or IP address of the network interface where the sever will listen.')
    parser.add_argument('--port', type=int, default=5000, help='The port to listen at.')
    args = parser.parse_args()

    dotenv.load_dotenv()

    app = FastAPI(
        title='SQL-Bot REST API',
        routes=[
            Route('/', endpoint=_redirect_root_to_docs)
        ]
    )
    langserve.add_routes(
        app,
        runnable=_create_api_chain(),
        path='/sql-bot',
        enabled_endpoints=['invoke', 'stream']
    )

    uvicorn.run(app, host=args.bind, port=args.port)


if __name__ == '__main__':
    main()
