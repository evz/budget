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
        if self.message.lower().startswith('how much'):
            return self.inquiry()
        elif 'owe' in self.message.lower():
            return self.addIOU()
        elif self.message.lower().startswith('add'):
            return self.addPerson()

    def addPerson(self):
        '''
        Example: "Add Eric 3125555555"
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

            return '"{name}" with phone number {number} successfully added'.format(name=name,
                                                                                   number=phone_number)

        else:
            raise PermissionError("Sorry, you can't do that", self.from_number)

    def addIOU(self):
        '''
        Example: "Eric owes Kristi $100"
                 "I owe Kristi $75"
                 "Kristi owes me $50"
        '''

        try:
            ower_name, owee = self.message.lower().replace('owes', 'owe').split('owe')
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
            raise MessageError('Amount "{}" should be a number'.format(amount),
                               self.from_number)

        if ower_name.strip() == 'i':
            ower = Person.query.filter(Person.phone_number == self.from_number).one()
            owee = self.findPerson(owee_name)
        elif owee_name.strip() == 'me':
            owee = Person.query.filter(Person.phone_number == self.from_number).one()
            ower = self.findPerson(ower_name)
        else:
            ower = self.findPerson(ower_name)
            owee = self.findPerson(owee_name)

        date_added = TIMEZONE.localize(datetime.now())

        iou = IOU(ower=ower,
                  owee=owee,
                  date_added=date_added,
                  amount=float(amount))

        db.session.add(iou)
        db.session.commit()

        return self.balance(ower, owee)

    def inquiry(self):
        """
        Example: "How much does Eric owe Kristi?"
        """

        try:
            _, ower_name, _, owee_name = self.message.lower().rsplit(' ', 3)

        except ValueError:
            raise MessageError('Balance inquiry should look like '
                               '"How much does <person 1 name> owe '
                               '<person 2 name>?"', self.from_number)

        ower = self.findPerson(ower_name)
        owee = self.findPerson(owee_name.replace('?', ''))

        return self.balance(ower, owee)

    def balance(self, ower, owee):
        owes = IOU.query.filter(IOU.ower == ower)\
                        .filter(IOU.owee == owee).all()
        ower_total = sum(o.amount for o in owes)

        owed = IOU.query.filter(IOU.ower == owee)\
                        .filter(IOU.owee == ower).all()
        owee_total = sum(o.amount for o in owed)

        balance =  int(ower_total - owee_total)

        fmt_args = {
            'ower': ower.name.title(),
            'owee': owee.name.title(),
            'balance': balance,
        }

        if balance == 0:
            message = '{ower} and {owee} are now even'.format(**fmt_args)
        elif balance > 0:
            message = '{ower} now owes {owee} ${balance}'.format(**fmt_args)
        elif balance < 0:
            fmt_args['balance'] = abs(fmt_args['balance'])
            message = '{owee} now owes {ower} ${balance}'.format(**fmt_args)

        return message


    def findPerson(self, person_name):
        person_name = person_name.strip()

        try:
            condition = Person.name.ilike('%{}%'.format(person_name))
            person = Person.query.filter(condition).one()
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
