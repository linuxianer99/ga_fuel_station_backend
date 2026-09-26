import logging
import socket
from oneprint import EscPosPrint
from jinja2 import Template


logging.basicConfig(level=logging.DEBUG)


class RemotePrinter(object):

    def __init__(self, printer_id, ip_address, recipe_template, port=9100, timeout=5):
        self.id = printer_id
        self.ip_address = ip_address
        self.recipe_template = recipe_template
        self.port = int(port)
        self.timeout = float(timeout)
    
    def CompileJob(self, rf):
        logging.info("Compile Job for printer: %s", self.id)
        with open(self.recipe_template) as f:
            recipe_content = Template(f.read()).render(
                date=rf["date"],
                aircraft=rf['aircraft'],
                amount=rf['amount'],
                article=rf['article']
            )
        ep = EscPosPrint()
        ep.auto_print(recipe_content)        
        return ep.get_data()
    
    def PrintJob(self, data):
        logging.info("Sending print job to %s at %s:%s", self.id, self.ip_address, self.port)
        with socket.create_connection((self.ip_address, self.port), timeout=self.timeout) as printer:
            printer.sendall(data)
        logging.info("Print job sent to %s (%s bytes)", self.id, len(data))
        return len(data)
