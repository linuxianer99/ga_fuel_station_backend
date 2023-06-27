from datetime import datetime
import logging
import json
import time
import requests


logging.basicConfig(level=logging.DEBUG)      

class TelegramBOT(object):
    msg = ""
    api_key = ""
    user_id = ""

    def __init__(self, api_key, user_id):
        self.api_key = api_key
        self.user_id = user_id

    def compile(self,rf):
         self.msg="\
            Refueling at: " + datetime.now().strftime('%Y-%m-%d  %H:%M') + "\n \
            Customer: " + rf['memberid'] + "\n \
            Aircraft: " +  rf['aircraft'] + "\n \
            Sort: " + rf['article'] + "\n \
            Amount: " + str(rf['amount'])
        
    def send(self):
        url = 'https://api.telegram.org/bot' + self.api_key + '/sendMessage'
        data={'chat_id': self.user_id, 'text': self.msg}

        #'parse_mode':'HTML',
        response = requests.get(url, data=data)

        logging.debug(response.json())
        
        #  if tel_resp.status_code == 200:
        #      logging.info("Telegram message sent!")
        #  else:
        #      logging.error("Telegram message could NOT be sent")

        #refueling_message="\
        #    ⛽️ " + datetime.now().strftime('%Y-%m-%d  %H:%M') + "\n \
        #    ✈️ " + data['aircraft'] + "\n \
        #    🛢 " +  data['amount']

        #\n {}\n{data['sort']}\n{}l"
        
       


