import streamlit as st
import snowflake.connector



def initialize_connection(schema_name):
    account_identifier = st.secrets["account_identifier"]
    user = st.secrets["user"]
    password = st.secrets["password"]
    database_name = st.secrets["database_name"]
    schema_name = schema_name
    warehouse_name = st.secrets["warehouse_name"]
    role_name = st.secrets["user"]
    conn_string = f"snowflake://{user}:{password}@{account_identifier}/{database_name}/{schema_name}?warehouse={warehouse_name}&role={role_name}"

    return conn_string

def snowflake_connection_user_input():
    st.session_state['user']=st.sidebar.text_input('Snowflake Username', 'Enter Snowflake Username')
    st.session_state['password']=st.sidebar.text_input('Snowflake Password', 'Enter Snowflake Password', type="password")
    st.session_state['warehouse']=st.sidebar.text_input('Snowflake Warehouse', 'Enter Snowflake Warehouse')
    st.session_state['database']=st.sidebar.text_input('Snowflake Database', 'Enter Snowflake Database')
    st.session_state['schema']=st.sidebar.text_input('Snowflake Schema', 'Enter Snowflake Schema')


def connect_to_snowflake():
    snowflake_connection_user_input()   
    ctx = snowflake.connector.connect(
        user=st.session_state['user'],
        password=st.session_state['password'],
        account=st.session_state['account'],
        warehouse=st.session_state['warehouse'],
        database=st.session_state['database'],
        schema=st.session_state['schema'],
        client_session_keep_alive=True
    )
    return ctx

if __name__ == '__main__':
    initialize_connection(schema_name=st.secrets["schema_name"])