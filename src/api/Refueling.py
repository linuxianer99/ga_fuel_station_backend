#from datetime import datetime
import logging
#import json
import datetime
from data_storage_db import storage

logging.basicConfig(level=logging.DEBUG)

# Read configuration
#with open("../config.json", "r") as jsonfile:
#    config = json.load(jsonfile)
#    logging.info("Configuration Read successful: %s", config)

date_format = '%d.%m.%Y'


db = storage()

class Refueling(object):
    amount = 0
    aircraft = ""
    totalizer = 0
    memberid = 0
    article = ""
    terminal_id= ""
    date = datetime.date(1970, 1, 1)

    def __init__(self, args):
        
        self.aircraft = args['aircraft']
        self.article = args['article']
        self.amount = args['amount']
        self.memberid = args['memberid']
        self.date = datetime.datetime.strptime(args['date'], date_format)
        if 'totalizer' in args:
            self.totalizer = args['totalizer']

    def set_terminal_id(self, terminal_id):
        self.terminal_id = terminal_id

    def get(self):
        content = {
            'aircraft': self.aircraft,
            'article': self.article,
            'amount': self.amount,
            'totalizer': self.totalizer,
            'memberid': self.memberid,
            'terminal_id': self.terminal_id,
            'date': self.date.strftime("%Y-%m-%d")
            }
        return content
    
    def store(self):
        return db.store_refueling(self)
    
