from os import path

app_dir= path.abspath(path.dirname(__file__))

class Config:
  AVATARS_DIR = path.join(app_dir, 'avatars')
  SQLALCHEMY_TRACK_MODIFICATIONS = False
  UPLOAD_MAX_SIZE = 4 * 1024 * 1024  # 4 MB
  ALLOWED_UPLOAD_TYPES = set(['image/jpeg', 'image/png'])

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
