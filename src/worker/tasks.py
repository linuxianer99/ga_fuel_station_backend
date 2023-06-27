import os
import time
import json
import logging
from celery import Celery
from celery.utils.log import get_task_logger
from celery import app
from celery.signals import task_failure

from vf_interface import vereinsflieger
from telegram_bot import TelegramBOT

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = get_task_logger(__name__)

env=os.environ

# Read configuration
with open("../config.json", "r") as jsonfile:
    config = json.load(jsonfile)
    logging.info("Configuration Read successful: %s", config)

# connect to Vereinsflieger
vf=vereinsflieger(config["vf"]["url"])

# Telegram
tg=TelegramBOT(config['telegram']['api_key'], config['telegram']['user_id']) 

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery.task(name='tasks.addsale')
# Create Sale in VF
def addsale(rf):
    if config['vf']['enable']:
        logger.info('[task] addsale:' + str(rf))
        vf.signin(config["vf"]["user"], config["vf"]["pwd_md5"], config["vf"]["appkey"])
        vf.add_sale(rf)
        vf.signout()
    else:
        logger.info('[task] addsale: DISABLED')

@celery.task(name='tasks.sendmessage')
# Send message to telegram
def sendmessage(rf):
    tg.compile(rf)
    tg.send()