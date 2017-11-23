from datetime import datetime

from pytz import timezone

from .models import IOU, Person

from .database import db

TIMEZONE = timezone('America/Chicago')


class MessageError(Exception):
    def __init__(self, message):
        self.message = message


class MessageHandler(object):
    def __init__(self, message):
        self.message = message

    def __call__(self):
        if 'owes' in self.message:
            return self.owes()
        elif 'spend' in self.message:
            return self.spend()

    def owes(self):
        ower_name, owee = message.lower().split('owes')
        owee_name, amount = owee.rsplit(' ', 1)

        try:
            amount = float(amount)
        except ValueError:
            raise MessageError('Amount "{}" should be a number')

        ower_condition = Person.name.ilike('%{}%'.format(ower_name))
        ower = db.session.query(Person).filter(ower_condition).one()

        owee_condition = Person.name.ilike('%{}%'.format(owee_name))
        owee = db.session.query(Person).filter(owee_condition).one()

        date_added = TIMEZONE.localize(datetime.now())

        iou = IOU(ower=ower,
                  owee=owee,
                  date_added=date_added,
                  amount=float(amount))
