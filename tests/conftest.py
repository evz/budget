import os
import pytest
from uuid import uuid4

from pytest_postgresql.factories import (
    init_postgresql_database, drop_postgresql_database, get_config,
)

from budget import create_app
from budget.database import db as _db
from budget.models import Person, person_to_person
from budget.utils import Client


DB_USER = 'postgres'
DB_HOST = ''
DB_PW = ''
DB_PORT = 5432
DB_NAME = 'budget_test'

DB_OPTS = dict(
    user=DB_USER,
    host=DB_HOST,
    pw=DB_PW,
    port=DB_PORT,
    name=DB_NAME
)

DB_FMT = 'postgresql://{user}:{pw}@{host}:{port}/{name}'

DB_CONN = DB_FMT.format(**DB_OPTS)


class FakeMessages(object):
    def create(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture(scope='session')
def database(request):
    pg_host = DB_OPTS.get("host")
    pg_port = DB_OPTS.get("port")
    pg_user = DB_OPTS.get("user")
    pg_db = DB_OPTS.get("name", "tests")

    # Create our Database.
    init_postgresql_database(pg_user, pg_host, pg_port, pg_db)

    # Ensure our database gets deleted.
    @request.addfinalizer
    def drop_database():
        drop_postgresql_database(pg_user, pg_host, pg_port, pg_db, 9.6)


@pytest.fixture(scope='session')
def app(request, database):
    """Session-wide test `Flask` application."""
    settings_override = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': DB_CONN
    }
    app = create_app(__name__, settings_override)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app


@pytest.fixture(scope='function')
def db(app, request):

    _db.app = app
    _db.create_all()

    def teardown():
        _db.drop_all()

    request.addfinalizer(teardown)

    return _db


# @pytest.fixture(scope='function')
# def db_session(db, request):
#     """Creates a new database session for a test."""
#     connection = db.engine.connect()
#     transaction = connection.begin()
#
#     options = dict(bind=connection, binds={})
#     session = db.create_scoped_session(options=options)
#
#     db.session = session
#
#     def teardown():
#         transaction.rollback()
#         connection.close()
#         session.remove()
#
#     request.addfinalizer(teardown)
#     return session

@pytest.fixture(scope='function')
def setup(db, request):
    eric = Person(name='eric',
                  phone_number='+13125555555',
                  admin=True)
    kristi = Person(name='kristi',
                    phone_number='+13126666666')

    eric_to_kristi = person_to_person.insert()\
                                     .values(from_phone='+13125555555',
                                             to_phone='+13126666666',
                                             alias='kristi')

    kristi_to_eric = person_to_person.insert()\
                                     .values(from_phone='+13126666666',
                                             to_phone='+13125555555',
                                             alias='eric')

    db.session.add(eric)
    db.session.add(kristi)

    db.session.commit()

    db.session.execute(eric_to_kristi)
    db.session.execute(kristi_to_eric)

    db.session.commit()

    @request.addfinalizer
    def remove_users():
        db.session.delete(eric)
        db.session.delete(kristi)
        db.session.commit()


@pytest.fixture(scope='function')
def twilio_mock(mocker):
    fake_messages = FakeMessages()
    mocker.patch.object(Client, 'messages', new=fake_messages)

    return fake_messages
