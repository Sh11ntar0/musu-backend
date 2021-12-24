""" Get access tokens
by Daiki Sguihara
"""
import json
import logging
import os
import sys
from typing import Dict

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


def get_object() -> Dict:
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


def lambda_handler(event, context):
    """ Get access token
    Args:
        event: APIGateway event
        context: context
    Returns:
        access token
    """
    current_obj = get_object()

    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET"
        },
        'body': json.dumps(current_obj)
    }
