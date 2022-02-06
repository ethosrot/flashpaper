from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth

db = SQLAlchemy()
cors = CORS()
httpauth = HTTPBasicAuth()

def init_app():
  app = Flask(__name__, instance_relative_config=False)
  app.config.from_object('config.DevelopmentConfig')

  # Initialize
  db.init_app(app)
  cors.init_app(app)

  with app.app_context():
    from . import auth, routes
    db.create_all()
    return app