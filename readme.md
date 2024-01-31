# Kai SQL Bot

## How to start the bot?

The bot runs as a Streamlit web application and opens up in you browser. In order to start it please
follow the steps below. They create a new python virtual environment, install the required libraries
and start the Streamlit web application.

You will also need the `.env` file which gives the application all the API keys
and other configuration parameters that it requires for its operation. Please copy the `.env.template`
file and fill the values. Create a symbolic link or copy the `.env` file to `.streamlit/secrets.toml` file.

```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
streamlit run app.py
```

The application should now be running on [http://localhost:8501](http://localhost:8501) and you should see it in your browser.


## How to start the REST API server for the bot?

The SQL-Bot agent can be started behind a REST API server that provides endpoints for sending queries to the agent.
The API and the agent are stateless, however, the endpoints allow to send the chat history as well as the new question.
The server is powered by [Langserve](https://github.com/langchain-ai/langserve)
and [FastAPI](https://fastapi.tiangolo.com/).

Starting the server is simple and involves the steps below. Please note, that you will also need the `.env` file as
for running the streamlit UI app.

```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
python3 restapi.py
```

The server listens on `localhost:5000` by default and exposes Swagger UI on http://localhost:5000/docs. You can change
these defaults by adding `--host <ip-or-hostname>` or `--port <port-number>` when starting `restapi.py` script.
The parameters and their description can be seen when running `python3 restapi.py --help` command.
