""" Update Instagram refresh token
By Daiki Sugihara
"""
from datetime import datetime, timezone
import json
import logging
import os
import sys
from typing import Dict

import boto3
import requests

s3 = boto3.resource('s3')

INSTAGRAM_ENDPOINT = "https://graph.instagram.com/refresh_access_token"

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


def get_object():
    """ Retrieve file from S3
    Returns:
         Retrieved object from sr
    """
    logging.info('start.')

    bucket = s3.Bucket(os.environ['STORAGE'])
    obj = bucket.Object(os.environ['OBJ_NAME'])
    response = obj.get()

    logging.info('end.')

    return json.loads(response['Body'].read())


def update_refresh_token(current_obj: Dict):
    """
    response looks like this
    {
      "access_token":"{long-lived-user-access-token}",
      "token_type": "bearer",
      "expires_in": 5183944 // Number of seconds until token expires
    }
    """
    logging.info(f'start.current_obj={current_obj}')

    res = requests.get(INSTAGRAM_ENDPOINT, params={
        'grant_type': 'ig_refresh_token',
        'access_token': current_obj['instagram']['currentToken']['accessToken']
    })

    logging.info('end.')

    return res.json()


def create_new_object(content: Dict, new_token: Dict):
    """ Update S3 file
    Args:
        content (Dict): file data in S3
        new_token (str): retrieved refresh token from INSTAGRAM
    Returns:
         Retrieved object from sr
    """
    logging.info(f'start. content={content}, new_token={new_token}')

    # Backup current data
    content['instagram']['oldToken'] = content['instagram']['currentToken'].copy()

    # Update contents
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    content['instagram']['currentToken']['accessToken'] = new_token['access_token']
    content['instagram']['currentToken']['createdTime'] = current_time

    logging.info('end.')

    return content


def update_object(new_content: Dict):
    """ Update INSTAGRAM refresh token
    Args:
        new_content: latest token info
    """
    logging.info(f'start. new_content={new_content}')

    bucket = s3.Object(os.environ['STORAGE'], os.environ['OBJ_NAME'])
    bucket.put(Body=json.dumps(new_content))

    logging.info('end.')


def lambda_handler(event, context):
    """ Update INSTAGRAM refresh token
    Args:
        event: APIGateway event
        context: context
    """
    logging.info('start.')

    current_obj: Dict = get_object()
    new_token = update_refresh_token(current_obj)
    new_content = create_new_object(current_obj, new_token)
    update_object(new_content)

    logging.info('end.')

    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET"
        }
    }
