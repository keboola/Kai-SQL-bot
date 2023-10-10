import os
import streamlit as st
import sqlalchemy
from streamlit_ace import st_ace, LANGUAGES, THEMES, KEYBINDINGS
from sqlalchemy import create_engine, text

image_path = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="KAI SQL Compiler", page_icon=":robot_face:")
st.image(image_path+'/../static/keboola_logo.png', width=200)
st.header("Kai SQL Compiler ")

account_identifier = st.secrets["account_identifier"]
user = st.secrets["user"]
password = st.secrets["password"]
database_name = st.secrets["database_name"]
schema_name = st.secrets["schema_name"]
warehouse_name = st.secrets["warehouse_name"]
role_name = st.secrets["role_name"]
conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"

engine = create_engine(conn_string)
st.write(st.session_state.query)

query = '''
SELECT "Order_ID", "Sales"
FROM "orders"
ORDER BY "Sales" ASC
LIMIT 10
'''

content = st_ace(
    value = query,
    language= LANGUAGES[145],
    theme=THEMES[3],
    keybinding=KEYBINDINGS[3],
    font_size=16,
    min_lines=15,
)

if st.button("Execute SQL"):
    with engine.connect() as connection:
        result = connection.execute(text(content))
        results = result.fetchall()
        st.table(results)
