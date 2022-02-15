from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from werkzeug.middleware.proxy_fix import ProxyFix
from os import environ

db = SQLAlchemy()
#cors = CORS()
httpauth = HTTPBasicAuth()

def init_app():
  app = Flask(__name__, instance_relative_config=False)

  # Check if we're globally set to development mode
  if environ.get('FLASK_ENV') == "production":
    app.config.from_object('config.ProductionConfig')
  else:
    print("Development environment detected. DB will be created in memory.")
    app.config.from_object('config.DevelopmentConfig')

  # Check if we're behind a HTTPS Proxy
  if environ.get('FLASHPAPER_PROXIED') == "true":
    print("Proxy mode set.")
    app.wsgi_app = ProxyFix(app.wsgi_app)

  # Initialize
  db.init_app(app)
  with app.app_context():
    from . import auth, routes
    db.create_all()

    return app
    