from flask import Blueprint, current_app

from .models import IOU

views = Blueprint('views', __name__)

@views.route('/incoming/', methods=['POST'])
def owe():
    if request.form.get('From') in current_app.config['OK_NUMBERS']:
        message = request.form['Body']
    else:
        abort(401)

    ower, owee = message.lower().split('owes')
    print(ower, owee)

    owee, amount = owee.rsplit(' ', 1)

    print(ower.strip(), owee.strip(), amount.strip())

    return 'owe'
