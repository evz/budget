from datetime import datetime

from pytz import timezone

from flask import current_app

from sqlalchemy.orm.exc import NoResultFound, FlushError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

import phonenumbers
from phonenumbers import PhoneNumberFormat

from twilio.rest import Client

from .models import IOU, Person, person_to_person

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
        self.message = message.strip()
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

            try:
                db.session.add(person)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

                raise MessageError('A person with the phone '\
                                   'number {1} already exists'.format(name, phone_number),
                                   self.from_number)

            friend = person_to_person.insert().values(from_phone=self.from_number,
                                                      to_phone=phone_number,
                                                      alias=name.lower())

            try:
                db.session.execute(friend)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                real_friend = db.session.query(person_to_person)\
                                        .filter(person_to_person.c.alias == name.lower())\
                                        .filter(person_to_person.c.from_phone == self.from_number)\
                                        .one()

                raise MessageError('You already have a friend named {0} '
                                   'with the number {1}'.format(name, real_friend.to_phone),
                                   self.from_number)

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

        ower_name, owee_name, amount, reason = self.parseMessage()

        try:
            amount = amount.replace('$', '')
            amount = float(amount)
        except ValueError:
            raise MessageError('Amount "{}" should be a number'.format(amount),
                               self.from_number)

        sender, receiver, sent_from_ower = self.findRelationship(ower_name, owee_name)

        if self.from_number not in [sender.phone_number, receiver.phone_number]:
            raise MessageError("Sorry, you can't record IOUs"
                               "that you are not part of", self.from_number)

        date_added = TIMEZONE.localize(datetime.now())

        if sent_from_ower:
            iou = IOU(ower=sender,
                      owee=receiver,
                      date_added=date_added,
                      amount=float(amount),
                      reason=reason)
        else:
            iou = IOU(ower=receiver,
                      owee=sender,
                      date_added=date_added,
                      amount=float(amount),
                      reason=reason)

        db.session.add(iou)
        db.session.commit()

        return self.balance(iou.ower, iou.owee)

    def parseMessage(self):
        try:
            if ' for ' in self.message.lower():
                people, reason = self.message.lower().split(' for ')
                ower_name, owee = people.replace('owes', 'owe').split('owe')
            else:
                ower_name, owee = self.message.lower().replace('owes', 'owe').split('owe')
                reason = 'General'
            owee = owee.strip()
            ower_name = ower_name.strip()
            owee_name, amount = owee.rsplit(' ', 1)
        except ValueError:
            raise MessageError('IOU message should look like: '
                               '"<name> owes <name> <amount> for <reason>"',
                               self.from_number)

        return ower_name, owee_name, amount, reason

    def inquiry(self):
        """
        Example: "How much does Eric owe Kristi?"
                 "How much do I owe Kristi?"
                 "How much does Kristi owe me?"
        """

        try:
            _, ower_name, _, owee_name = self.message.lower().rsplit(' ', 3)

        except ValueError:
            raise MessageError('Balance inquiry should look like '
                               '"How much does <person 1 name> owe '
                               '<person 2 name>?"', self.from_number)

        sender, receiver, sent_from_ower = self.findRelationship(ower_name,
                                                                 owee_name.replace('?', ''))

        if sent_from_ower:
            return self.balance(sender, receiver)
        else:
            return self.balance(receiver, sender)

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

    def findRelationship(self, ower_name, owee_name):

        sender = Person.query.get(self.from_number)
        sent_from_ower = False

        if ower_name == owee_name:
            alias = ower_name
        elif ower_name in ['i', sender.name]:
            alias = owee_name
            sent_from_ower = True
        elif owee_name in ['me', sender.name]:
            alias = ower_name

        try:
            relationship = db.session.query(person_to_person)\
                                     .filter(person_to_person.c.from_phone == self.from_number)\
                                     .filter(person_to_person.c.alias == alias.lower())\
                                     .one()
        except NoResultFound:
            raise MessageError('"{0}" not found. '
                               'You can add this person '
                               'by texting back "Add {0} '
                               '<their phone number>'.format(alias),
                               self.from_number)

        receiver = Person.query.get(relationship.to_phone)

        return sender, receiver, sent_from_ower


    def validatePhoneNumber(self, phone_number):
        parsed = phonenumbers.parse(phone_number, 'US')

        if not phonenumbers.is_valid_number(parsed):
            raise MessageError('"{}" is not a valid '
                               'phone number'.format(phone_number),
                               self.from_number)

        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

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
