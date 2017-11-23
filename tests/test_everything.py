from flask import url_for

from budget.models import Person, IOU

def test_add_iou(db_session, client, setup):
    data = {
        'Body': 'Eric owes Kristi $100',
        'From': '+13125555555'
    }

    rv = client.post(url_for('views.incoming'), data=data)

    iou = db_session.query(IOU).filter(IOU.amount == 100.0).first()
    eric = db_session.query(Person).filter(Person.name == 'Eric').first()
    kristi = db_session.query(Person).filter(Person.name == 'Kristi').first()

    assert iou.ower == eric
    assert iou.owee == kristi
    assert iou.amount == 100.0
