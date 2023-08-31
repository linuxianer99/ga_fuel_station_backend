import os
import time
import json
import logging

import smtplib, ssl
from jinja2 import Template
from datetime import datetime
import paho.mqtt.client as mqtt

from celery import Celery
from celery.utils.log import get_task_logger
from celery import app
from celery.signals import task_failure

from vf_interface import vereinsflieger
from telegram_bot import TelegramBOT
from remote_printer import RemotePrinter
from remote_printer import handlePrinter


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

# Define logger
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
#file_handler = logging.FileHandler('logs.log')
#file_handler.setLevel(logging.DEBUG)
#file_handler.setFormatter(formatter)
#logger = logging.getLogger()
#logger.addHandler(file_handler)

# Remote Printers
Printers = []
# Parse config for printers
for key, value in os.environ.items():
    if key.startswith("PRINTER_NAME_"):
        logger.info('[RemotePrinter] add: ' + value)
        Printers.append(RemotePrinter(value, value + '.j2'))

# Setup Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery.task(name='tasks.log')
#Write to log
def log(lm):
    print(lm)
    #logger.info(lm['terminal_id'] + ':' + lm['message'])

@celery.task(name='tasks.vf_addsale')
# Create Sale in VF
def addsale(rf):
    if int(os.environ.get('VF_ENABLE', '1')) == 1:
        logger.info('[task] addsale:' + str(rf))
        vf.signin(os.environ.get('VF_USER', ''), os.environ.get('VF_PWD', ''), os.environ.get('VF_APPKEY', ''))
        vf.add_sale(rf)
        vf.signout()
    else:
        logger.info('[task] addsale: DISABLED')

@celery.task(name='tasks.tg_sendmessage')
# Send message to telegram
def tg_sendmessage(rf):
    if int(os.environ.get('TG_ENABLE', '1')) == '1':
        tg.compile(rf)
        tg.send()

@celery.task(name='tasks.vf_recipe')
def vf_recipe(rf):
    if int(os.environ.get('VF_ENABLE', '0')) == '1':
        logger.info('[task] send recipe to user:' + str(rf))
        vf.signin(os.environ.get('VF_USER', ''), os.environ.get('VF_PWD', ''), os.environ.get('VF_APPKEY', ''))
        props = vf.get_properties_from_id(rf['memberid'])
        vf.signout()
        try: 
            recipe_string = props.get('Tankbeleg')
            logging.info("Recipe found: %s", recipe_string)
            recipes = dict(x.split(":") for x in recipe_string.split(","))
            logging.info("Recipes:")
            logging.info(recipes)
        except:
            logging.info("No Recipe property found!")
            return True
        # Parse recipe string
        for type, target in recipes.items():
            if type == "email":
                logging.info("Recipe method: Email")
                logging.info("Send recipe to %s", target)

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
                    server.sendmail(sender_email, 
                                    target, message)

            elif type == "printer":
                    printer = target
                    current_printer = next((p for p in Printers if p.id == printer), None)
                    
                    if current_printer is not None:
                        job = current_printer.CompileJob(rf)
                        result = current_printer.PrintJob(job)
                        logging.info("Print result:")
                        logging.info(result)
                    else:
                        logging.info("Requested printer not registered!") 
        
    else:
        logger.info('[task] vf_recipe: DISABLED')