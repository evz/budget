from flask import Blueprint, current_app, request, abort


from .models import IOU
from .utils import IOUHandler, MessageError, PermissionError, sendTwilioResponse
from .database import db

views = Blueprint('views', __name__)


@views.route('/pong/')
def pong():

    try:
        from deployment import DEPLOYMENT_ID
    except ImportError:
        abort(401)

    return DEPLOYMENT_ID


@views.route('/incoming/', methods=['POST'])
def incoming():

    message = request.form.get('Body')
    from_number = request.form.get('From')

    if message and from_number:
        iou = IOUHandler(message, from_number)
        response = iou.handle()
    else:
        abort(400)

    sendTwilioResponse(response, from_number)

    return 'iou handled'


@views.app_errorhandler(MessageError)
def error(exception):

    sendTwilioResponse(exception.message, exception.from_number)

    return 'exception handled'


@views.app_errorhandler(PermissionError)
def permission_error(exception):
    abort(401)
