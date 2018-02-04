from flask import Blueprint, current_app, request, abort, render_template


from .database import db

admin = Blueprint('admin', __name__)

@admin.route('/')
def index():
    return render_template('index.html')


@admin.route('/my-account/')
def my_account():
    return render_template('my-account.html')
