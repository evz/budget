from datetime import datetime

from pytz import timezone

from flask import current_app

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import text

import phonenumbers
from phonenumbers import PhoneNumberFormat

from twilio.rest import Client

from .models import IOU, Person

from .database import db

TIMEZONE = timezone('America/Chicago')


class MessageError(Exception):
    def __init__(self, message, from_number):
        self.message = message
        self.from_number = from_number

    def __str__(self):
        return self.message


class PermissionError(MessageError):
    pass


class IOUHandler(object):
    def __init__(self, message, from_number):
        self.message = message
        self.from_number = from_number

    def handle(self):
        if 'owes' in self.message.lower():
            return self.addIOU()
        elif self.message.lower().startswith('add'):
            return self.addPerson()

    def addPerson(self):
        '''
        Example: "Add Eric 3126599476"
        '''
        if self.fromAdmin():

            try:
                _, name, number = self.message.split(' ', 2)
            except ValueError:
                raise MessageError('"Add person" message should '
                                   'look like: "Add <name> <phone number>"',
                                   self.from_number)

            phone_number = self.validatePhoneNumber(number)

            person = Person(name=name,
                            phone_number=phone_number)

            db.session.add(person)
            db.session.commit()
        else:
            raise PermissionError("Sorry, you can't do that", self.from_number)

    def addIOU(self):
        '''
        Example: "Eric owes Kristi $100"
        '''

        try:
            ower_name, owee = self.message.lower().split('owes')
            owee = owee.strip()
            owee_name, amount = owee.rsplit(' ', 1)
        except ValueError:
            raise MessageError('IOU message should look like: '
                               '"<name> owes <name> <amount>"',
                               self.from_number)

        try:
            amount = amount.replace('$', '')
            amount = float(amount)
        except ValueError:
            raise MessageError('Amount "{}" should be a number',
                               self.from_number)

        ower = self.findPerson(ower_name)
        owee = self.findPerson(owee_name)

        date_added = TIMEZONE.localize(datetime.now())

        iou = IOU(ower=ower,
                  owee=owee,
                  date_added=date_added,
                  amount=float(amount))

        db.session.add(iou)
        db.session.commit()

        totals = '''
            SELECT (
              SELECT SUM(amount)
              FROM iou
              WHERE ower_id = :ower_id
                AND owee_id = :owee_id
            ) - (
              SELECT SUM(amount)
              FROM iou
              WHERE ower_id = :owee_id
                AND owee_id = :ower_id
            ) AS total
        '''

        total = db.session.execute(text(totals),
                                   ower_id=ower.id,
                                   owee_id=owee.id).first().total

        fmt_args = {
            'ower': ower.name.title(),
            'owee': owee.name.title(),
            'total': abs(total),
        }

        if total == 0:
            message = '{ower} and {owee} are now even'.format(**fmt_args)
        elif total > 0:
            message = '{ower} now owes {owee} ${total}'.format(**fmt_args)
        elif total < 0:
            message = '{owee} now owes {ower} ${total}'.format(**fmt_args)

        return message

    def findPerson(self, person_name):
        person_name = person_name.strip()

        try:
            condition = Person.name.ilike('%{}%'.format(person_name))
            person = db.session.query(Person).filter(condition).one()
        except NoResultFound:
            raise MessageError('"{0}" not found. '
                               'You can add this person '
                               'by texting back "Add {0} '
                               '<their phone number>'.format(person_name),
                               self.from_number)
        return person


    def validatePhoneNumber(self, phone_number):
        parsed = phonenumbers.parse(phone_number, 'US')

        if not phonenumbers.is_valid_number(parsed):
            raise MessageError('"{}" is not a valid '
                               'phone number'.format(phone_number),
                               self.from_number)

        return  phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

    def fromAdmin(self):
        admin = db.session.query(Person)\
                          .filter(Person.phone_number == self.from_number)\
                          .first()
        if admin:
            return admin.admin


def sendTwilioResponse(message, to_number):

    account_id = current_app.config['TWILIO_ACCOUNT_ID']
    auth_token = current_app.config['TWILIO_AUTH_TOKEN']
    from_number = current_app.config['TWILIO_NUMBER']

    client = Client(account_id, auth_token)
    message = client.messages.create(to=to_number,
                                     from_=from_number,
                                     body=message)
