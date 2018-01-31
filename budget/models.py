from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID

from .database import db

def get_uuid():
    return str(uuid4())

class IOU(db.Model):
    __tablename__ = 'iou'
    id = db.Column(UUID, primary_key=True, default=get_uuid)
    ower_id = db.Column(UUID, db.ForeignKey('person.id'), nullable=False)
    owee_id = db.Column(UUID, db.ForeignKey('person.id'), nullable=False)

    ower = db.relationship('Person',
                           backref='ious',
                           primaryjoin="Person.id == IOU.ower_id")

    owee = db.relationship('Person',
                           backref='uoms',
                           primaryjoin="Person.id == IOU.owee_id")

    amount = db.Column(db.Float)
    date_added = db.Column(db.DateTime(timezone=True))
    pending = db.Column(db.Boolean, default=True)
    reason = db.Column(db.Text)

    def __repr__(self):
        return '<IOU %r owes %r $%r>' % (self.ower, self.owee, self.amount)

class Person(db.Model):
    __tablename__ = 'person'
    id = db.Column(UUID, primary_key=True, default=get_uuid)
    name = db.Column(db.String, unique=True)
    phone_number = db.Column(db.String(15))
    admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Person %r>' % self.name
