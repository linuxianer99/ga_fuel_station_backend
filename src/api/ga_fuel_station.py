from flask import g, Flask, request, render_template, Response
from flask_restful import Resource, reqparse
import time
from datetime import datetime
import logging
import os
import json
import ssl
import hashlib
import hmac
import base64
from Refueling import Refueling

from prometheus_client import multiprocess
from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST, Gauge, Info, Counter, Enum

from worker import celery

terminals = ['terminal']

REFUELINGS = Counter('refuelings', 'How much refuelings happen')
LASTPINGDELAY = Gauge('terminal_last_ping', 'Delay between pings', labelnames=terminals)
WRONGAUTH = Counter('wrong_auth', 'Counter of wrong authcode')
FREEHEAP = Gauge('freeheap', 'Free Heap Memory', labelnames=terminals)
REBOOTREASON = Gauge('rebootreason', 'Reason for last reboot', labelnames=terminals)
IP = Info('IP', 'Current IP of Terminal')
STATUS = Enum('terminal_state', 'state of the terminal', 
              states=['normal', 'connection_error', 'blocked'], labelnames=terminals)

i = Info('GA_Fuelstation', 'Name of Software')
i.info({'version': '1.0.0', 'buildhost': 'foo@bar'})

terminal_inventory = {}

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

@app.route('/terminal/<terminal_id>/ping', methods=['GET'])
def terminal_ping(terminal_id):
    logging.info("Ping from %s", terminal_id)
    if terminal_id not in terminals:
        terminals.append(terminal_id)
    if terminal_id not in terminal_inventory:
        terminal_properties={'last_seen': time.time(), 'delta': 0}
        logging.info("Terminal %s seen the first time", terminal_id)
        terminal_inventory[terminal_id]=terminal_properties
    else:
        logging.info("Terminal %s seen again", terminal_id)
        delta = time.time()-terminal_inventory[terminal_id]['last_seen']
        terminal_properties={'last_seen': time.time(), 'delta': delta}
        terminal_inventory.update({terminal_id: terminal_properties})

    LASTPINGDELAY.labels(terminal_id).set(terminal_properties['delta'])
    logging.info(terminal_inventory)
    return "PONG"

@app.route('/terminal/<terminal_id>/status', methods=['POST'])
def terminal_status(terminal_id):
    logging.info("Status from %s", terminal_id)
    data = request.get_json()
    logging.info(data)
    
    lm = {}
    lm['terminal_id'] = terminal_id
    lm['message'] = data
    task = celery.send_task('tasks.log', args=[lm], kwargs={})

    if terminal_id not in terminals:
        terminals.append(terminal_id)
    if terminal_id not in terminal_inventory:
        terminal_properties={'last_seen': time.time(), 'delta': 0}
        logging.info("Terminal %s seen the first time", terminal_id)
        terminal_inventory[terminal_id]=terminal_properties
    else:
        logging.info("Terminal %s seen again", terminal_id)
        delta = time.time()-terminal_inventory[terminal_id]['last_seen']
        terminal_properties={'last_seen': time.time(), 'delta': delta}
        terminal_inventory.update({terminal_id: terminal_properties})

    LASTPINGDELAY.labels(terminal_id).set(terminal_properties['delta'])
    FREEHEAP.labels(terminal_id).set(data['freeheap'])
    IP.info({'Terminal': terminal_id, 'IP:': data['ip']})
    if "reboot_reason" in data:
        REBOOTREASON.labels(terminal_id).set(data['reboot_reason'])
    
    if data['status'] == 0:
        STATUS.labels(terminal_id).state('normal')
    if data['status'] == 1:
        STATUS.labels(terminal_id).state('connection_error')
    if data['status'] == 2:
        STATUS.labels(terminal_id).state('blocked')

    return "Success", 200

@app.route('/terminal/<terminal_id>', methods=['POST'])
def terminal_refueling(terminal_id):
    data = request.get_json()
    logging.debug(data)
    if verify_data(data):
        rf = Refueling(data)
        rf.set_terminal_id(terminal_id)
        # Write to database 
        db_id = rf.store()
        # Trigger further tasks if refueling is above limit
        booking_threshold = float(os.environ.get('BOOKING_THRESHOLD', '0.0'))
        if float(rf.get()['amount']) > booking_threshold:
            task = celery.send_task('tasks.vf_addsale', args=[rf.get()], kwargs={})
            task = celery.send_task('tasks.tg_sendmessage', args=[rf.get()], kwargs={})
            task = celery.send_task('tasks.vf_recipe', args=[rf.get()], kwargs={})
        else:
            logging.info("Amount below booking threshold => no booking done!")

        # Handle prometheus
        REFUELINGS.inc()

        return "Success", 200
    else:
        WRONGAUTH.inc()
        return "Wrong AuthCode", 403    
        

@app.route("/version", methods=['GET'])
def version():
    return "V1.0", 200

@app.route("/metrics")
def metrics():
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    return Response(data, mimetype=CONTENT_TYPE_LATEST)       

def verify_data(data):
    secret_key = base64.b64decode((os.environ.get('TERMINAL_KEY', '')))
    message = data['aircraft']+data['memberid']+str(data['amount'])+data['article']
    hmac_value = hmac.new(secret_key, message.encode("utf-8"), hashlib.sha256)
    digest = hmac_value.digest()
    calculated_hash = base64.b64encode(digest).decode()
    if (calculated_hash.strip()==data['auth']):
        logging.info("API auth OK")
        return True
    else:
        logging.info("API auth FAIL")
        return False


#parser = reqparse.RequestParser()
#parser.add_argument('amount')
#parser.add_argument('totalizer')
#parser.add_argument('sort')
#parser.add_argument('aircraft')

#@app.route('/', methods=['GET', 'POST'])
#def entry_mask():
#    aircraft = request.args.get('aircraft')
#    sort = request.args.get('sort')
#    return render_template('index.html', aircraft=aircraft, sort=sort, articles=config['article']['fuel'])

#@app.route('/submit_refueling', methods=['POST'])
#def submit_refueling():
#    args = request.form.to_dict()
#    print(args)
#    rf = Refueling(args)
#    rf.plausibilize()

    # Create Sale in VF
#    if config["vf"]["enable"] == 1:
#        vf.signin(config["vf"]["user"], config["vf"]["pwd_md5"], config["vf"]["appkey"])
#        vf.add_sale(rf.get())
#        vf.signout()

    # Store to database
#    if config["database"]["enable"] == 1:
#        storage.process_refueling(rf.get())

    # Publish message of refueling
    #logging.info("MQTT: Publish message ..")
    #logging.debug("Message %s", rf.asJsonStr())
    #ret = g.client.publish(g.config['mqtt']['topic'], rf.asJsonStr())

    # Trigger printer if necessary
    #if 'print_recipe' in args:
    #    logging.info("MQTT: Publish message .. for printing")
    #    logging.debug("Message %s", rf.asJsonStr())
    #    ret = g.client.publish(g.config['mqtt']['printer_topic'], rf.asJsonStr())

 #   return  render_template('recipe.html', aircraft=args['aircraft'], sort=args['sort'], amount=args['amount'])