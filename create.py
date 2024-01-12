import streamlit as st
import json
import re 
from kbcstorage.configurations import Configurations

COMPONENT_ID = 'keboola.snowflake-transformation'
BRANCH_ID = 'default'

def create_snowflake_transformation(sql_query: str):
    """
    Create a new Snowflake transformation in.

    Args:
    sql_query (str): The SQL query to be used in the Snowflake transformation.

    This function creates a Streamlit interface for user input and submits the
    configuration to Keboola.
    """
    _display_transformation_form(sql_query)

def _prepare_snowflake_configuration(sql_query: str, output_table_name: str):
    """
    Prepare the Snowflake transformation configuration JSON.

    Args:
    sql_query (str): The SQL query to be used in the transformation.
    output_table_name (str): The name of the output table.

    Returns:
    dict: The configuration JSON for the Snowflake transformation.
    """
    configuration_template = {
    "parameters": {
        "blocks": [
        {
            "name": "Block 1",
            "codes": [
            {
                "name": "Code",
                "script": [
                f"CREATE OR REPLACE TABLE \"{output_table_name}\" AS (\n{sql_query}\n)"
                ]
            }
            ]
        }
        ]
    },
    "storage": {
        "input": {
        "tables": []
        },
        "output": {
        "tables": [
            {
            "destination": f"out.c-kai-sql-bot.{output_table_name}",
            "source": f"{output_table_name}"
            }
        ]
        }
    }
    }

    return configuration_template

def _display_transformation_form(sql_query: str):
    """
    Display a form in Streamlit for transformation details and handle submission.

    Args:
    sql_query (str): The SQL query to be used in the transformation.
    
    """
    with st.form(key="transformation_details", clear_on_submit=True):
        tr_name = st.text_input('Transformation name')
        tr_description = st.text_area('Transformation description')
        output_table_name = st.text_input('Output table name')
        if st.form_submit_button("Create"):
            configuration = _prepare_snowflake_configuration(sql_query, output_table_name)
            _create_transformation_in_keboola(tr_name, tr_description, configuration)
            
def _create_transformation_in_keboola(name: str, description: str, configuration: dict):
    """
    Create a new transformation in Keboola.

    Args:
    name (str): The name of the transformation.
    description (str): The description of the transformation.
    configuration (dict): The JSON configuration for the Snowflake transformation.
    """         
    try:
        configurations_client = Configurations(
            root_url = st.secrets['url'], 
            token = st.secrets['keboola_token'], 
            branch_id = BRANCH_ID
        )
        response = configurations_client.create(
            component_id = COMPONENT_ID,
            name = name,
            description = description,
            configuration = json.dumps(configuration)
        )
        st.success("Configuration created successfully: {}".format(response))
    except Exception as e:
        st.error("Error creating configuration: {}".format(e))