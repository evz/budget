from flask import url_for, current_app

from budget.models import Person, IOU
from budget.views import Client

from .conftest import FakeMessages


def test_add_iou(db_session, client, setup):
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

    db_session.delete(iou)
    db_session.commit()


def test_add_person(db_session, client, setup):
    data = {
        'Body': 'Add Foo +13129999999',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    person = db_session.query(Person).filter(Person.name == 'Foo').first()

    assert person.name == 'Foo'
    assert not person.admin
    assert person.phone_number == '+13129999999'

    db_session.delete(person)
    db_session.commit()


def test_iou_missing_person(db_session, client, setup, mocker):

    fake_messages = FakeMessages()
    mocker.patch.object(Client, 'messages', new=fake_messages)

    data = {
        'Body': 'Foo owes Eric $300',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert fake_messages.kwargs['to'] == data['From']
    assert fake_messages.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert fake_messages.kwargs['body'] == '"foo" not found. '\
                                           'You can add this person by '\
                                           'texting back "Add foo <their phone number>'


def test_add_person_bad_number(db_session, client, setup, mocker):
    fake_messages = FakeMessages()
    mocker.patch.object(Client, 'messages', new=fake_messages)

    data = {
        'Body': 'Add Foo 444',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert fake_messages.kwargs['to'] == data['From']
    assert fake_messages.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert fake_messages.kwargs['body'] == '"444" is not a valid phone number'


def test_bad_iou(db_session, client, setup, mocker):
    fake_messages = FakeMessages()
    mocker.patch.object(Client, 'messages', new=fake_messages)

    data = {
        'Body': 'Owes 300',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert fake_messages.kwargs['to'] == data['From']
    assert fake_messages.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert fake_messages.kwargs['body'] == 'IOU message should look like: '\
                                           '"<name> owes <name> <amount>"'


def test_bad_add_person(db_session, client, setup, mocker):
    fake_messages = FakeMessages()
    mocker.patch.object(Client, 'messages', new=fake_messages)

    data = {
        'Body': 'Add floop',
        'From': '+13125555555',
    }

    client.post(url_for('views.incoming'), data=data)

    assert fake_messages.kwargs['to'] == data['From']
    assert fake_messages.kwargs['from_'] == current_app.config['TWILIO_NUMBER']
    assert fake_messages.kwargs['body'] == '"Add person" message should '\
                                           'look like: "Add <name> <phone number>"'

