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

#from dotenv import load_dotenv
#load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = get_task_logger(__name__)

env=os.environ

# Read configuration
#with open("config.json", "r") as jsonfile:
#    config = json.load(jsonfile)
#    logging.info("Configuration Read successful: %s", config)

# connect to Vereinsflieger
vf=vereinsflieger(os.environ.get('VF_URL', 'www.vereinsflieger.de'))

# Telegram
tg=TelegramBOT(os.environ.get('TG_APIKEY', ''), os.environ.get('TG_USERID', '')) 

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery.task(name='tasks.addsale')
# Create Sale in VF
def addsale(rf):
    if os.environ.get('VF_ENABLE', '0'):
        logger.info('[task] addsale:' + str(rf))
        vf.signin(os.environ.get('VF_USER', ''), os.environ.get('VF_PWD', ''), os.environ.get('VF_APPKEY', ''))
        vf.add_sale(rf)
        vf.signout()
    else:
        logger.info('[task] addsale: DISABLED')

@celery.task(name='tasks.sendmessage')
# Send message to telegram
def sendmessage(rf):
    tg.compile(rf)
    tg.send()