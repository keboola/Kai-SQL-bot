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

