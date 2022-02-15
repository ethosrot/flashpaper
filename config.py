from distutils.util import strtobool
from os import path, environ

app_dir= path.abspath(path.dirname(__file__))

class Config:
  AVATARS_DIR = path.join(app_dir, 'avatars')
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  UPLOAD_MAX_SIZE = 4 * 1024 * 1024  # 4 MB
  ALLOWED_UPLOAD_TYPES = set(['image/jpeg', 'image/png'])

  try:
    MAX_WEBHOOKS = int(environ.get("FLASHPAPER_WEBHOOKS_MAX", '3'))
  except (TypeError, ValueError):
    print("Invalid value for FLASHPAPER_WEBHOOKS_MAX. Defaulting to 3.")
    MAX_WEBHOOKS = 3

  try:
    WEBHOOKS_ENABLED = strtobool(environ.get("FLASHPAPER_WEBHOOKS_ENABLED", 'False'))
  except ValueError:
    print("Invalid value for FLASHPAPER_WEBHOOKS_ENABLED. Defaulting to False.")
    WEBHOOKS_ENABLED = False

  try:
    IS_PROXIED = strtobool(environ.get("FLASHPAPER_USING_PROXY", "False"))
  except ValueError:
    print("Invalid value for FLASHPAPER_USING_PROXY. Defaulting to False.")
    IS_PROXIED = False

class ProductionConfig(Config):
  SQLALCHEMY_DATABASE_URI = "sqlite:///{}".format(path.join(app_dir, 'data', 'flashpaper.db'))
  FLASK_ENV = 'production'
  DEBUG = False
  TESTING = False

class DevelopmentConfig(Config):
  SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
  FLASK_ENV = 'development'
  DEBUG = True
  TESTING = True
