import logging
import json

class Refueling:
    amount = 0
    aircraft = ""
    totalizer = 0
    sort = ""

    def __init__(self, args) -> None:
        self.aircraft = args['aircraft']
        self.sort = args['sort']
        self.amount = args['amount']
        if 'totalizer' in args:
            self.totalizer = args['totalizer']
        

    def plausibilize(self):
        logging.info("Plausibilitation done!")
       
    def asJsonStr(self):
        content = {
            'aircraft': self.aircraft,
            'sort': self.sort,
            'amount': self.amount,
            'totalizer': self.totalizer,
            }
        return json.dumps(content)
    
    def get(self):
        content = {
            'aircraft': self.aircraft,
            'sort': self.sort,
            'amount': self.amount,
            'totalizer': self.totalizer,
            }
        return content 