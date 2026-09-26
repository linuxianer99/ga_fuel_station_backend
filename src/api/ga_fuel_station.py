from flask import g, Flask, request, render_template, Response, jsonify
from werkzeug.middleware.dispatcher import DispatcherMiddleware
#from flask_restful import Resource, reqparse
import time
#from datetime import datetime
import logging
import os
import math
#import json
#import ssl
import hashlib
import hmac
import base64
from Refueling import Refueling, parse_refueling_date

from prometheus_client import multiprocess, make_wsgi_app
from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST, Gauge, Info, Counter, Enum

from worker import celery

app = Flask(__name__)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

terminals = ['terminal']

REFUELINGS = Counter('refuelings', 'How much refuelings happen')
LASTPINGDELAY = Gauge('terminal_last_ping', 'Delay between pings', labelnames=terminals)
WRONGAUTH = Counter('wrong_auth', 'Counter of wrong authcode')
FREEHEAP = Gauge('freeheap', 'Free Heap Memory', labelnames=terminals)
REBOOTREASON = Gauge('rebootreason', 'Reason for last reboot', labelnames=terminals)
IP = Info('IP', 'Current IP of Terminal')
#STATUS = Enum('terminal_state', 'state of the terminal', 
#              states=['normal', 'connection_error', 'blocked'], labelnames=terminals)
STATUS = Gauge('terminal_status', 'Current terminal status', labelnames=terminals)
RSSI = Gauge('wifi_rssi', 'Current RSSI of WIFI signal', labelnames=terminals)
TIMESTAMP = Gauge('terminal_status_timestamp', 'Time of last status message as UNIX-Timestamp', labelnames=terminals)

terminal_inventory = {}

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')


def _is_finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _validate_status_payload(data):
    if not isinstance(data, dict):
        return ['JSON body must be an object']

    errors = []
    for field in ('freeheap', 'status'):
        if field not in data:
            errors.append('{} is required'.format(field))
        elif not _is_finite_number(data[field]):
            errors.append('{} must be a finite number'.format(field))

    ip_address = data.get('ip')
    if not isinstance(ip_address, str) or not ip_address.strip() or len(ip_address) > 255:
        errors.append('ip must be a non-empty string of at most 255 characters')

    for field in ('reboot_reason', 'rssi'):
        if field in data and not _is_finite_number(data[field]):
            errors.append('{} must be a finite number'.format(field))

    if 'freeheap' in data and _is_finite_number(data['freeheap']) and data['freeheap'] < 0:
        errors.append('freeheap must not be negative')
    return errors


def _validate_refueling_payload(data):
    if not isinstance(data, dict):
        return ['JSON body must be an object']

    errors = []
    for field in ('aircraft', 'memberid', 'article', 'date', 'auth'):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append('{} must be a non-empty string'.format(field))
        elif len(value) > 128:
            errors.append('{} must be at most 128 characters'.format(field))

    amount = data.get('amount')
    if not _is_finite_number(amount) or amount <= 0:
        errors.append('amount must be a finite number greater than 0')

    if 'totalizer' in data:
        totalizer = data['totalizer']
        if not _is_finite_number(totalizer) or totalizer < 0:
            errors.append('totalizer must be a finite non-negative number')

    date_value = data.get('date')
    if isinstance(date_value, str):
        try:
            parse_refueling_date(date_value)
        except ValueError:
            errors.append('date must use DD.MM.YYYY or ISO 8601 format')

    return errors


def _invalid_request(errors):
    return jsonify({'error': 'Invalid request body', 'details': errors}), 400

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
    data = request.get_json(silent=True)
    errors = _validate_status_payload(data)
    if errors:
        return _invalid_request(errors)
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
    IP.info({'Terminal': terminal_id, 'IP': data['ip']})
    if "reboot_reason" in data:
        REBOOTREASON.labels(terminal_id).set(data['reboot_reason'])
    
    STATUS.labels(terminal_id).set(data['status'])

    if "rssi" in data:
        RSSI.labels(terminal_id).set(data['rssi'])

    TIMESTAMP.labels(terminal_id).set(int(time.time()))

    return "Success", 200

@app.route('/terminal/<terminal_id>', methods=['POST'])
def terminal_refueling(terminal_id):
    data = request.get_json(silent=True)
    errors = _validate_refueling_payload(data)
    if errors:
        return _invalid_request(errors)
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

#@app.route("/metrics")
#def metrics():
#    registry = CollectorRegistry()
#    multiprocess.MultiProcessCollector(registry)
#    data = generate_latest(registry)
#    return Response(data, mimetype=CONTENT_TYPE_LATEST)       

def verify_data(data):
    secret_key = base64.b64decode((os.environ.get('TERMINAL_KEY', '')))
    message = data['aircraft']+data['memberid']+str(data['amount'])+data['article']+data['date']
    hmac_value = hmac.new(secret_key, message.encode("utf-8"), hashlib.sha256)
    digest = hmac_value.digest()
    calculated_hash = base64.b64encode(digest).decode()
    if hmac.compare_digest(calculated_hash.strip(), data['auth']):
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
