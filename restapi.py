import dotenv
import langserve
from fastapi import FastAPI
from starlette.responses import RedirectResponse

import app as agent_specs

dotenv.load_dotenv()
app = FastAPI()


@app.get('/')
async def redirect_root_to_docs():
    return RedirectResponse('/docs')


agent = agent_specs._create_agent(agent_specs._Model.GPT_4_TURBO, agent_specs._Toolkit.WAII)
langserve.add_routes(app, agent, path='/sql-bot', enabled_endpoints=['invoke', 'stream'])


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='127.0.0.1', port=8000)
