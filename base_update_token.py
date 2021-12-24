""" Update BASE refresh token
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
from selenium import webdriver

BASE_ENDPOINT = 'https://api.thebase.in'
BASE_SHOP_URL = 'https://musu.official.ec'
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']

EMAIL = os.environ['EMAIL']
PW = os.environ['PW']

POST_TOKEN_URL = "https://api.thebase.in/1/oauth/token"
GRANT_TYPE_AUTHCODE = 'authorization_code'

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

s3 = boto3.resource('s3')


def get_authorize_code():
    """ Get authorize code from base
    Returns:
        code (str): Authorize code
    """
    logging.info('start.')

    url = f'{BASE_ENDPOINT}/1/oauth/authorize?response_type=code&client_id={CLIENT_ID}&' \
          f'redirect_uri={BASE_SHOP_URL}&scope=read_items'

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--single-process")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--window-size=880x996")
    options.add_argument("--no-sandbox")
    options.add_argument("--homedir=/tmp")
    options.binary_location = "/opt/python/bin/headless-chromium"

    driver = webdriver.Chrome(
        "/opt/python/bin/chromedriver",
        options=options
    )
    driver.set_page_load_timeout(5)

    driver.get(url)

    mail_box = driver.find_element_by_name('data[User][mail_address]')
    mail_box.send_keys(EMAIL)

    pw_box = driver.find_element_by_name('data[User][password]')
    pw_box.send_keys(PW)

    auth_button = driver.find_element_by_name('auth_yes')
    auth_button.click()

    tmp = driver.current_url.split("=")[1]
    code = tmp.split("&")[0]
    driver.quit()

    logging.info('finish.')

    return code


def get_refresh_token(auth_code: str):
    """ Get refresh token from BASE
    Args:
        auth_code (str): Authorize code
    Returns:
        str: retrieved refresh token
    """
    logging.info('start.')

    param = {
        'grant_type': GRANT_TYPE_AUTHCODE,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': auth_code,
        'redirect_uri': BASE_SHOP_URL,
    }

    response = requests.post(POST_TOKEN_URL, params=param)
    token = json.loads(response.text)
    logging.info(f'finish. Retrieved token: {token}')

    return token["refresh_token"]


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


def create_new_object(content: Dict, refresh_token: str):
    """ Update S3 file
    Args:
        content (Dict): file data in S3
        refresh_token (str): retrieved refresh token from BASE
    Returns:
         Retrieved object from sr
    """
    logging.info(f'start. content={content}, new_token={refresh_token}')

    # Backup current data
    content['base']['oldToken'] = content['base']['currentToken'].copy()

    # Update contents
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    content['base']['currentToken']['accessToken'] = refresh_token
    content['base']['currentToken']['createdTime'] = current_time

    logging.info('end.')

    return content


def update_object(new_content: Dict):
    """ Update BASE refresh token
    Args:
        new_content: latest token info
    """
    logging.info('start.')

    bucket = s3.Object(os.environ['STORAGE'], os.environ['OBJ_NAME'])
    bucket.put(Body=json.dumps(new_content))

    logging.info('end.')


def lambda_handler(event, context):
    """ Update BASE refresh token
    Args:
        event: APIGateway event
        context: context
    """
    logging.info('start.')

    auth_code = get_authorize_code()
    refresh_token = get_refresh_token(auth_code)

    current_obj = get_object()
    new_content = create_new_object(current_obj, refresh_token)
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


if __name__ == '__main__':
    lambda_handler("", "")
