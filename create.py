import json
from typing import Any, Mapping

import streamlit as st
from kbcstorage.client import Client
from kbcstorage.configurations import Configurations
from requests import RequestException

COMPONENT_ID = 'keboola.snowflake-transformation'
BRANCH_ID = 'default'


def get_transformation_url(api_response: Mapping[str, Any]) -> str:
    url = st.secrets['keboola_url'].rstrip('/')
    token_info = Client(url, st.secrets['keboola_token']).tokens.verify()
    return f'{url}/admin/projects/{token_info["owner"]["id"]}/transformations-v2/{COMPONENT_ID}/{api_response["id"]}'


def create_snowflake_transformation(
        *, sql_query: str, name: str, description: str, output_table_name: str
) -> Mapping[str, Any]:
    """
    Create a new Snowflake transformation in.

    :param sql_query: The SQL query to be used in the Snowflake transformation.
    :param name: The name of the transformation.
    :param description: The description of the transformation.
    :param output_table_name: The name of the transformation's output table.

    :return: The parsed JSON from the Storage API response.
    """
    config = _prepare_snowflake_configuration(sql_query, output_table_name)
    return _create_transformation_in_keboola(name, description, config)


def _prepare_snowflake_configuration(sql_query: str, output_table_name: str) -> Mapping[str, Any]:
    """
    Prepare the Snowflake transformation configuration.

    :param sql_query: The SQL query to be used in the transformation.
    :param output_table_name: The name of the output table.

    :return: The configuration dictionary for the Snowflake transformation.
    """
    return {
        'parameters': {
            'blocks': [
                {
                    'name': 'Block 1',
                    'codes': [
                        {
                            'name': 'Main',
                            'script': [
                                f'CREATE OR REPLACE TABLE \"{output_table_name}\" AS (\n{sql_query}\n)'
                            ]
                        }
                    ]
                }
            ]
        },
        'storage': {
            'input': {
                'tables': []
            },
            'output': {
                'tables': [
                    {
                        'destination': f'out.c-kai-sql-bot.{output_table_name}',
                        'source': f'{output_table_name}'
                    }
                ]
            }
        }
    }


def _create_transformation_in_keboola(
        name: str, description: str, configuration: Mapping[str, Any]
) -> Mapping[str, Any]:
    """
    Create a new transformation in Keboola.

    :param name: The name of the transformation.
    :param description: The description of the transformation.
    :param configuration: The JSON configuration for the Snowflake transformation.

    :return: The parsed JSON from the Storage API response.
    """
    configurations_client = Configurations(
        root_url=st.secrets['keboola_url'],
        token=st.secrets['keboola_token'],
        branch_id=BRANCH_ID
    )
    return configurations_client.create(
        component_id=COMPONENT_ID,
        name=name,
        description=description,
        configuration=json.dumps(configuration)
    )
