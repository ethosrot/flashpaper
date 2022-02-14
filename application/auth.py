from application import httpauth
from .models import User, UserAvatar, UserStatus, UserFollow
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

@httpauth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        return user
    return False

def create_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user is not None:
        print("User already exists.")
        return
    if not re.match(pattern=r"^[a-zA-Z0-9_]{1,40}$", string=username):
        print("Invalid username.")
        return
    new_user = User(username=username, password=generate_password_hash(password, method='sha256'))
    new_user.avatar = UserAvatar()
    new_user.status_data = UserStatus()
    new_user.last_updated = datetime.utcnow().replace(microsecond=0)
    new_user.follows_updated = datetime.utcnow().replace(microsecond=0)
    new_user.save()
    print("User '{}' created.".format(username))

def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        print("User does not exist.")
        return
    user.delete()
    print("User '{}' deleted".format(username))