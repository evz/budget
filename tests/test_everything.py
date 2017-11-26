import phonenumbers
from phonenumbers import PhoneNumberFormat

from flask import url_for, current_app

from budget.models import Person, IOU


def test_add_iou(db, client, setup, twilio_mock):
    data = {
        'Body': 'Eric owes Kristi $100',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    iou = db.session.query(IOU).filter(IOU.amount == 100.0).first()
    eric = db.session.query(Person).filter(Person.name == 'eric').first()
    kristi = db.session.query(Person).filter(Person.name == 'kristi').first()

    assert iou.ower == eric
    assert iou.owee == kristi
    assert iou.amount == 100.0
    assert iou.pending

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == 'Eric now owes Kristi $100'

    data = {
        'Body': 'Eric owes Kristi $100',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Eric now owes Kristi $200'

    data = {
        'Body': 'Kristi owes Eric $70',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Eric now owes Kristi $130'

    data = {
        'Body': 'Kristi owes Eric $200',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Kristi now owes Eric $70'

    data = {
        'Body': 'How much does Eric owe Kristi?',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Kristi now owes Eric $70'

    data = {
        'Body': 'How much does Kristi owe Eric?',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Kristi now owes Eric $70'

    data = {
        'Body': 'I owe Kristi $100',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Eric now owes Kristi $30'

    data = {
        'Body': 'Kristi owes me $100',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Kristi now owes Eric $70'

    data = {
        'Body': 'How much do I owe Kristi?',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Kristi now owes Eric $70'

    data = {
        'Body': 'How much does Kristi owe me?',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Kristi now owes Eric $70'

    for iou in IOU.query.all():
        db.session.delete(iou)


def test_bad_amount(client, setup, twilio_mock):
    data = {
        'Body': 'Eric owes Kristi poop',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == 'Amount "poop" should be a number'


def test_add_person(db, client, setup, twilio_mock):

    good_numbers = [
        ('+13129999999', 'foo',),
        ('+1 (312) 888-8888', 'floop',),
        ('(312) 888-7777', 'bloop',),
        ('312 777 8888', 'froop',),
        ('3126667777', 'groop',),
        ('312 888-0011', 'shoop',),
    ]

    for number, name in good_numbers:

        data = {
            'Body': 'Add {0} {1}'.format(name, number),
            'From': '+13125555555',
        }

        client.post(url_for('views.incoming'), data=data)

        person = db.session.query(Person).filter(Person.name == name).first()

        assert person.name == name
        assert not person.admin

        number = phonenumbers.format_number(phonenumbers.parse(number, 'US'),
                                            PhoneNumberFormat.E164)

        assert person.phone_number == number

        assert twilio_mock.kwargs['to'] == data['From']
        assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
        assert twilio_mock.kwargs['body'] == '"{name}" with phone number {number} successfully added'.format(name=name, number=number)

        db.session.delete(person)
        db.session.commit()


def test_iou_missing_person(db, client, setup, twilio_mock):

    data = {
        'Body': 'Foo owes Eric $300',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == '"foo" not found. '\
                                           'You can add this person by '\
                                           'texting back "Add foo <their phone number>'


def test_add_person_bad_number(db, client, setup, twilio_mock):

    bad_numbers = [
        '444',
    ]

    data = {
        'Body': 'Add Foo 444',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == '"444" is not a valid phone number'


def test_bad_iou(db, client, setup, twilio_mock):

    data = {
        'Body': 'Owes 300',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == 'IOU message should look like: '\
                                           '"<name> owes <name> <amount>"'


def test_bad_add_person(db, client, setup, twilio_mock):

    data = {
        'Body': 'Add floop',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == '"Add person" message should '\
                                           'look like: "Add <name> <phone number>"'


def test_bad_inquiry(db, client, setup, twilio_mock):

    data = {
        'Body': 'How much floop',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Balance inquiry should look like '\
                                         '"How much does <person 1 name> owe '\
                                         '<person 2 name>?"'
