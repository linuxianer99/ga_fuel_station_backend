from flask import g, Flask, request, render_template
from flask_restful import Resource, reqparse
import time
import logging
import os
import json
import ssl
import hashlib
import hmac
import base64
from Refueling import Refueling

from worker import celery

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Read configuration
#with open("../config.json", "r") as jsonfile:
#    config = json.load(jsonfile)
#    logging.info("Configuration Read successful: %s", config)

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


@app.route('/terminal/<terminal_id>', methods=['POST'])
def terminal_refueling(terminal_id):
    data = request.get_json()
    logging.info(data)
    if verify_data(data):
        rf = Refueling(data)
        rf.set_terminal_id(terminal_id)
        # Write to database 
        db_id = rf.store()
        task = celery.send_task('tasks.addsale', args=[rf.get()], kwargs={})
        task = celery.send_task('tasks.sendmessage', args=[rf.get()], kwargs={})
        return ("200")
    else:
        return ("500")    
        
        
       

def verify_data(data):
    secret_key = str.encode(os.environ.get('TERMINAL_KEY', '111111111'))
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
