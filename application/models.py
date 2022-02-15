from application import db
from flask_inputs import Inputs
from flask_inputs.validators import JsonSchema

class User(db.Model):
    __tablename__ = 'users'

    # Core User Data
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String)
    password = db.Column(db.String)
    last_updated = db.Column(db.DateTime)

    # User Configurables
    avatar = db.relationship('UserAvatar', uselist=False, backref='users', cascade='all, delete-orphan')
    status_data = db.relationship('UserStatus', uselist=False, backref='users', cascade='all, delete-orphan')

    # Following API
    follows = db.relationship('UserFollow', backref='users', lazy='dynamic', cascade='all, delete-orphan')
    follows_updated = db.Column(db.DateTime)

    # Flashpaper Webhooks API
    webhooks = db.relationship('UserWebhook', backref='users', lazy='dynamic', cascade='all, delete-orphan')

    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

class UserStatus(db.Model):
    __tablename__ = 'userstatuses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
 
    # User Status Data  
    name = db.Column(db.String)
    status = db.Column(db.String)
    emoji = db.Column(db.String)
    media = db.Column(db.String)
    media_type = db.Column(db.Integer)
    uri = db.Column(db.String)

class UserAvatar(db.Model):
    __tablename__ = 'avatars'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # User Avatar Data
    original = db.Column(db.String)
    original_key = db.Column(db.String)

class UserFollow(db.Model):
    __tablename__ = 'follows'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # User Follow Data
    username = db.Column(db.String)

class UserWebhook(db.Model):
    __tablename__ = 'webhooks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # User Webhook Data
    url = db.Column(db.String)
    method = db.Column(db.String)
    latest_response = db.Column(db.Integer)
    latest_timestamp = db.Column(db.DateTime)

class JsonLengthInputs(Inputs):
    json = [JsonSchema(schema={
        'type': 'object',
        'properties': {
            'name': {
                'maxlength': 40,
            }, 'status': {
                'maxLength': 100,
            }, 'media': {
                'maxLength': 100,
            }
        },
        'additionalProperties': True,
    })]

class JsonTypeInputs(Inputs):
    json = [JsonSchema(schema={
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string'
            }, 'status': {
                'type': 'string'
            }, 'emoji': {
                'type': 'string'
            }, 'media': {
                'type': 'string'
            }, 'media_type': {
                'type': 'integer'
            }, 'uri': {
                'type': 'string'
            }
        },
        'additionalProperties': True,
    })]