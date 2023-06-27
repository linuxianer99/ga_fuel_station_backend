from pony.orm import *
from datetime import datetime
import logging
import json
import time
import os

logging.basicConfig(level=logging.DEBUG)

db = Database()

class DB_Refueling(db.Entity):
    id = PrimaryKey(int, auto=True)
    aircraft = Required(str)
    memberid = Required(str)
    article = Required(str)
    amount = Required(float)
    totalizer = Optional(float)
    terminal_id = Required(str)
    create = Required(datetime, default=lambda: datetime.now())
    vf = Optional(datetime)
    msg = Optional(datetime)


class storage(object):
    def __init__(self):
        # connect to database
        logging.info("Connecting to database ...")
        retry_count = 0
        #set_sql_debug(True)
        retry = True
        while retry and retry_count < 20:
            try:
                result = db.bind(provider='mysql', \
                                host=os.environ.get('DB_SERVER', 'localhost'), \
                                user=os.environ.get('DB_USER', 'mlv'), \
                                passwd=os.environ.get('DB_PWD', 'mlv'), \
                                db=os.environ.get('DB_DATABASE', 'mlv_fuelstation'))
                result = db.generate_mapping(create_tables=True)
                retry = False
                logging.info("Database connection OK")
            except:
                retry_count = retry_count + 1
                retry = True
                time.sleep(5)
                logging.error("Database connection failed ... retrying ... %i ", retry_count)

    @db_session
    def store_refueling(self, rf):
        logging.info("Store to DB ...")
        db_item = DB_Refueling(
            aircraft = rf.aircraft,
            memberid = rf.memberid,
            article = rf.article,
            amount = rf.amount,
            terminal_id = rf.terminal_id
        )
        return db_item
