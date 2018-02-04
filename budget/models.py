from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import UniqueConstraint

from .database import db

def get_uuid():
    return str(uuid4())

class IOU(db.Model):
    __tablename__ = 'iou'
    id = db.Column(UUID, primary_key=True, default=get_uuid)
    ower_id = db.Column(db.String(15), db.ForeignKey('person.phone_number'), nullable=False)
    owee_id = db.Column(db.String(15), db.ForeignKey('person.phone_number'), nullable=False)

    ower = db.relationship('Person',
                           backref='ious',
                           primaryjoin="Person.phone_number == IOU.ower_id")

    owee = db.relationship('Person',
                           backref='uoms',
                           primaryjoin="Person.phone_number == IOU.owee_id")

    amount = db.Column(db.Float)
    date_added = db.Column(db.DateTime(timezone=True))
    pending = db.Column(db.Boolean, default=True)
    reason = db.Column(db.Text)

    def __repr__(self):
        return '<IOU %r owes %r $%r>' % (self.ower, self.owee, self.amount)


person_to_person = db.Table('person_to_person',
                            db.Column('from_phone',
                                      db.ForeignKey('person.phone_number'),
                                      primary_key=True),
                            db.Column('to_phone',
                                      db.ForeignKey('person.phone_number')),
                            db.Column('alias', db.String(), primary_key=True))

class Person(db.Model):
    __tablename__ = 'person'
    phone_number = db.Column(db.String(15), primary_key=True)
    name = db.Column(db.String)
    admin = db.Column(db.Boolean, default=False)

    friends = db.relationship('Person',
                              secondary=person_to_person,
                              primaryjoin='Person.phone_number == person_to_person.c.from_phone',
                              secondaryjoin='Person.phone_number == person_to_person.c.to_phone',
                              backref='friends_to_me')

    def __repr__(self):
        return '<Person %r (%r)>' % (self.name, self.phone_number, )
