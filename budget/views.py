from flask import Blueprint, current_app, request

from twilio.rest import Client

from .models import IOU
from .utils import IOUHandler, MessageError
from .database import db

views = Blueprint('views', __name__)

@views.route('/incoming/', methods=['POST'])
def incoming():

    message = request.form.get('Body')
    from_number = request.form.get('From')

    if message and from_number:
        iou = IOUHandler(message, from_number)
    else:
        abort(400)

    return 'iou handled'

@views.app_errorhandler(MessageError)
def error(exception):

    account_id = current_app.config['TWILIO_ACCOUNT_ID']
    auth_token = currnet_app.config['TWILIO_AUTH_TOKEN']
    from_number = current_app.config['TWILIO_NUMBER']

    client = Client(account_id, auth_token)
    message = client.messages.create(to=exception.from_number,
                                     from_=from_number,
                                     body=exception.message)

    return 'exception handled'
