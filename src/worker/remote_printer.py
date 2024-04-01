import os
import time
#import json
import logging
#from oneprint import EscPosPrint
from escpos.printer import Dummy
from jinja2 import Template
from datetime import datetime
import paho.mqtt.client as mqtt

# Topic:
# /printer/<printer_id>/heartbeat   => Printer send registration to server
# /printer/<printer_id>/job         => server send jobs to printer


logging.basicConfig(level=logging.DEBUG)


def getPrinters():
    logging.info("GetPrinters ...")
    return Printers

def handlePrinter(client, userdata, msg):
    logging.info("Message in topic: %s", msg.topic)
    # TODO:
    # Implement TOPIC Check !!!

    printer = msg.topic.split('/')[-2]
    logging.info("Printer ID: %s", printer)
    registered_printer = next((p for p in Printers if p.id == printer), None)
    if (registered_printer):
        logging.info("Heartbeat from Printer ID: %s", registered_printer.id)
        registered_printer.heartbeat()
    else:
        Printers.append(RemotePrinter(printer, client))
        logging.info("Registered Printer ID: %s", printer)
    
    logging.info("Current registered printers:")
    for printer in Printers:
        logging.info("Printer: %s", printer.id)

class RemotePrinter(object):

    id = ""
    last_seen = 0
    recipe_template = ""

    def __init__(self, printer_id, recipe_template):
        self.id = printer_id
        self.recipe_template = recipe_template

    def heartbeat(self):
        last_seen = time.time()
        logging.info("Hearbeat: %s", self.id)
    
    def CompileJob(self, rf):
        logging.info("Compile Job for printer: %s", self.id)
        # Generate Job metadata
        # Topic: /printer/<printer_id>/job         => server send jobs to printer

        # Compose recipe
        with open(self.recipe_template) as f:
            recipe_content = Template(f.read()).render(
                date=datetime.today().strftime('%Y-%m-%d'),
                time=datetime.today().strftime('%H:%M'),
                aircraft=rf['aircraft'],
                amount=rf['amount'],
                article=rf['article']
            )
        d = Dummy()
        d.text("Hallo welt")
        d.cut()
        logging.info("DATA: %s", d.output)
        return d.output
    
    def PrintJob(self, data):
        logging.info("Print Job on: %s", self.id)
        # Generate Job metadata
        # Topic: /printer/<printer_id>/job         => server send jobs to printer
        topic = "printer/" + self.id + "/job"
        print(topic)
        job = {'topic': topic, 'data': data}
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_message = handlePrinter
        client.connect(os.environ.get('BROKER_HOST', 'localhost'), int(os.environ.get('BROKER_PORT', '1883')))
        result = client.publish(topic, data)
        client.disconnect()
        return result
