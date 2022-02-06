from application import httpauth
from .models import User
from passlib.hash import sha256_crypt # Replace with werkzeug.security?


@httpauth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and sha256_crypt.verify(password, user.password):
        return user
    return False