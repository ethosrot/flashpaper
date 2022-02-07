from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from os import environ

db = SQLAlchemy()
#cors = CORS()
httpauth = HTTPBasicAuth()

def init_app():
  app = Flask(__name__, instance_relative_config=False)
  if environ.get('FLASK_ENV') == "production":
    app.config.from_object('config.ProductionConfig')
  else:
    print("Development environment detected. DB will be created in memory.")
    app.config.from_object('config.DevelopmentConfig')

  # Initialize
  db.init_app(app)
  with app.app_context():
    from . import auth, routes
    db.create_all()

    return app
    