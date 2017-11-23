from sqlalchemy.dialects.postgresql import UUID

from .database import db

class IOU(db.Model):
    __tablename__ = 'iou'
    id = db.Column(UUID, primary_key=True)
    ower_id = db.Column(UUID, db.ForeignKey('person.id'), nullable=False)
    ower = db.relationship('Person', backref=db.backref('ious', lazy=True))
    owee_id = db.Column(UUID, db.ForeignKey('person.id'), nullable=False)
    owee = db.relationship('Person', backref=db.backref('uoms', lazy=True))
    amount = db.Column(db.Float)
    date_added = db.Column(db.DateTime(timezone=True))

    def __repr__(self):
        return '<IOU %r owes %r $%r>' % (self.ower, self.owee, self.amount)

class Person(db.Model):
    __tablename__ = 'person'
    id = db.Column(UUID, primary_key=True)
    name = db.Column(db.String)
    phone_number = db.Column(db.String(15))
    admin = db.Column(db.Boolean)

    def __repr__(self):
        return '<Person %r>' % self.name
