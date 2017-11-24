import phonenumbers
from phonenumbers import PhoneNumberFormat

from flask import url_for, current_app

from budget.models import Person, IOU


def test_add_iou(db_session, client, setup, twilio_mock):
    data = {
        'Body': 'Eric owes Kristi $100',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    iou = db_session.query(IOU).filter(IOU.amount == 100.0).first()
    eric = db_session.query(Person).filter(Person.name == 'eric').first()
    kristi = db_session.query(Person).filter(Person.name == 'kristi').first()

    assert iou.ower == eric
    assert iou.owee == kristi
    assert iou.amount == 100.0

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == 'Eric now owes Kristi a total of $100'

    db_session.delete(iou)
    db_session.commit()

    data = {
        'Body': 'Eric owes Kristi $100',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Eric now owes Kristi a total of $200'

    data = {
        'Body': 'Kristi owes Eric $70',
        'From': '+13125555555'
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['body'] == 'Eric now owes Kristi a total of $130'


def test_bad_amount(client, setup, twilio_mocker):
    data = {
        'Body': 'Eric owes Kristi poop',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == 'Amount "poop" should be a number'


def test_add_person(db_session, client, setup):

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

        person = db_session.query(Person).filter(Person.name == name).first()

        assert person.name == name
        assert not person.admin

        number = phonenumbers.format_number(phonenumbers.parse(number, 'US'),
                                            PhoneNumberFormat.E164)

        assert person.phone_number == number

        db_session.delete(person)
        db_session.commit()


def test_iou_missing_person(db_session, client, setup, twilio_mock):

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


def test_add_person_bad_number(db_session, client, setup, twilio_mock):

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


def test_bad_iou(db_session, client, setup, twilio_mock):

    data = {
        'Body': 'Owes 300',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == 'IOU message should look like: '\
                                           '"<name> owes <name> <amount>"'


def test_bad_add_person(db_session, client, setup, twilio_mock):

    data = {
        'Body': 'Add floop',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert twilio_mock.kwargs['to'] == data['From']
    assert twilio_mock.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert twilio_mock.kwargs['body'] == '"Add person" message should '\
                                           'look like: "Add <name> <phone number>"'
