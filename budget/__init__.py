from flask import Flask

from flask_sqlalchemy import SQLAlchemy

from .views import views
from .admin import admin
from .database import db

def create_app(name=__name__, settings_override={}):
    app = Flask(name)
    config = '{0}.app_config'.format(__name__)
    app.config.from_object(config)

    for k,v in settings_override.items():
        app.config[k] = v

    db.init_app(app)

    app.register_blueprint(views)
    app.register_blueprint(admin)

    return app
