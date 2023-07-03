import os
import time
import json
import logging

import smtplib, ssl
from jinja2 import Template
from datetime import datetime

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

smtp_context = ssl.create_default_context()

port = os.environ.get('SMTP_PORT', '465')  # For SSL
smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
sender_email = os.environ.get('SMTP_SENDER', 'Tankstelle@localhost')  # Enter your address
user=os.environ.get('SMTP_USER', '')
password = os.environ.get('SMTP_PASSWORD', '')

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

@celery.task(name='tasks.tg_sendmessage')
# Send message to telegram
def tg_sendmessage(rf):
    tg.compile(rf)
    tg.send()

@celery.task(name='tasks.vf_sendrecipe')
def vf_sendrecipe(rf):
    if os.environ.get('VF_ENABLE', '0'):
        logger.info('[task] send recipe to user:' + str(rf))
        vf.signin(os.environ.get('VF_USER', ''), os.environ.get('VF_PWD', ''), os.environ.get('VF_APPKEY', ''))
        props = vf.get_properties_from_id(rf['memberid'])
        vf.signout()
        try: 
            recipe_contact = props.get('Tankbeleg')
        except:
            logging.info("No Recipe property found!")
            return True
        # Parse recipe string
        recipe_data = recipe_contact.split(':',1)
        if recipe_data[0] == "email":
            logging.info("Recipe method: Email")
            logging.info("Send recipe to %s", recipe_data[1])

            # Compose message
            with open('email.j2') as f:
                message = Template(f.read()).render(
                    date=datetime.now().strftime("%d-%m-%Y, %H:%M:%S"),
                    aircraft=rf['aircraft'],
                    amount=rf['amount'],
                    article=rf['article']
                )
            with smtplib.SMTP_SSL(smtp_server, port, context=smtp_context) as server:
                server.login(user, password)
                server.sendmail(sender_email, recipe_data[1], message)
    else:
        logger.info('[task] addsale: DISABLED')