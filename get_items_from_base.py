""" Retrieve items information from BASE
By Daiki Sugihara
"""
import json
import logging
import os
import sys
import traceback
from typing import Dict, List

import requests
import boto3

s3 = boto3.resource('s3')

# Set logging
logger = logging.getLogger()
for h in logger.handlers:
    logger.removeHandler(h)

h = logging.StreamHandler(sys.stdout)

FORMATTER = '[%(levelname)s] %(funcName)s(): %(message)s'
h.setFormatter(logging.Formatter(FORMATTER))
logger.addHandler(h)

level_name = os.environ['LOG_LEVEL']
level = logging.getLevelName(level_name)

logger.setLevel(level)

# BASE information to get an access token
BASE_SHOP_URL = 'https://musu.official.ec'
POST_TOKEN_URL = "https://api.thebase.in/1/oauth/token"
GRANT_TYPE_REFRESHTOKEN = 'refresh_token'
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']

# BASE information to get items
BASE_ITEMS_ENDPOINT = "https://api.thebase.in/1/items"

# BASE information to get items
BASE_CATEGORY_ENDPOINT = "https://api.thebase.in/1/categories"

REQUEST_SUCCESS = 200


def get_tokens() -> Dict:
    """ Get access token file content
    Returns:
         the content of file in s3
    """
    logging.info('start.')

    bucket = s3.Bucket(os.environ['STORAGE'])
    obj = bucket.Object(os.environ['OBJ_NAME'])
    response = obj.get()

    logging.info('end.')

    return json.loads(response['Body'].read())


def get_access_token(refresh_token: str) -> str:
    """ Issue a new access token using refresh token
    Args:
        refresh_token: refresh token stored in s3
    Returns:
        issued access token
    """
    logging.info(f'start.refresh_token={refresh_token}')

    param = {
        'grant_type': GRANT_TYPE_REFRESHTOKEN,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': refresh_token,
        'redirect_uri': BASE_SHOP_URL,
    }

    response = requests.post(POST_TOKEN_URL, params=param)
    token_data = json.loads(response.text)

    logging.info('end.')

    return token_data['access_token']


def get_category_ids(access_token: str) -> List:
    """ Get category information from Base
    Args:
        access_token: BASE access token
    Returns:
        response (Dict): category ids from BASE API
    """
    logging.info('start.')

    header = {
        "Authorization": "Bearer " + access_token
    }

    try:
        response = requests.get(BASE_CATEGORY_ENDPOINT, headers=header)

        return json.loads(response.content)
    except Exception as ex:
        raise ex

    finally:
        logging.info('end.')


def get_items(access_token: str, category_ids: List) -> Dict:
    """ Get registered items information from Base
    Args:
        access_token: BASE access token
        category_id: category id
    Returns:
        response (Dict): response from BASE API
    """
    logging.info(f'start. access_token={access_token}, category_ids={category_ids}')
    items = {}
    try:
        for category in category_ids['categories']:
            category_id = category['category_id']
            param = {
                # 'visible': "1",
                "max_image_no": '10',
                'order': 'created',
                'sort': 'desc',
                'category_id': category_id,
            }

            header = {
                "Authorization": "Bearer " + access_token
            }

            response = requests.get(BASE_ITEMS_ENDPOINT, params=param, headers=header)

            items[category_id] = (json.loads(response.content)['items'])

        return items

    except Exception as ex:
        raise ex
    finally:
        logging.info('end.')


def lambda_handler(event, context):
    """ Retrieve items information from BASE
    Args:
        event: APIGateway event
        context: context
    Returns:
        Retrieved items information from BASE
    """
    logging.info(f'start.event={event}')

    try:
        tokens = get_tokens()
        refresh_token = tokens['base']['currentToken']['accessToken']
        access_token = get_access_token(refresh_token)

        category_ids: List = get_category_ids(access_token)
        items = get_items(access_token, category_ids)
        print('items', items)

        return {
            'statusCode': 200,
            'headers': {
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET"
            },
            'body': json.dumps(items)
        }
    except Exception as ex:
        logging.error(f'failed.\n {traceback.format_exc()}')
    finally:
        logging.info('end.')
