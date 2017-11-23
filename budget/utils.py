from datetime import datetime

from pytz import timezone

import phonenumbers
from phonenumbers import PhoneNumberFormat

from .models import IOU, Person

from .database import db

TIMEZONE = timezone('America/Chicago')


class MessageError(Exception):
    def __init__(self, message, from_number):
        self.message = message
        self.from_number = from_number

    def __str__(self):
        return self.message


class IOUHandler(object):
    def __init__(self, message, from_number):
        self.message = message
        self.from_number = from_number

    def __call__(self):
        if 'owes' in self.message:
            return self.addIOU()
        elif self.message.lower().startswith('add'):
            return self.addPerson()

    def addPerson(self):
        '''
        Example: "Add Eric 3126599476"
        '''
        if self.fromAdmin():

            try:
                _, name, number = self.message.split(' ')
            except ValueError:
                raise MessageError('"Add person" message should '
                                   'look like: "Add <name> <phone number>"',
                                   self.from_number)

            phone_number = self.validatePhoneNumber(number)

            person = Person(name=name,
                            phone_number=phone_number)

            db.session.add(person)
            db.session.commit()

    def addIOU(self):
        '''
        Example: "Eric owes Kristi $100"
        '''

        try:
            ower_name, owee = message.lower().split('owes')
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

    def findPerson(self, person_name):
        try:
            condition = Person.name.ilike('%{}%'.format(person_name))
            person = db.session.query(Person).filter(condition).one()
        except NoResultsFound:
            raise MessageError('"{0}" not found. '
                               'You can add this person '
                               'by texting back "Add "{0}" '
                               '<their phone number>'.format(ower_name))
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
