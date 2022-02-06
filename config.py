from os import environ, path

app_directory = path.abspath(path.dirname(__file__))

class Config:
  AVATARS_DIR = path.join(app_directory, 'avatars')
  APP_SECRET = environ.get('APP_SECRET')
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
  UPLOAD_MAX_SIZE = 4 * 1024 * 1024  # 4 MB
  ALLOWED_UPLOAD_TYPES = set(['image/jpeg', 'image/png'])

class ProductionConfig(Config):
  FLASK_ENV = 'production'
  DEBUG = False
  TESTING = False

class DevelopmentConfig(Config):
  FLASK_ENV = 'development'
  DEBUG = True
  TESTING = True
