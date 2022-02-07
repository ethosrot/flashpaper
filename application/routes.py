# Application Imports
from application import db, httpauth
from .models import JsonLengthInputs, JsonTypeInputs, User, UserFollow
from flask import current_app as app
from rfc3986 import is_valid_uri, normalize_uri
import re

# Main Imports
from flask import Response, request, json, send_from_directory
from flask_cors import cross_origin
from emoji_data import EmojiSequence

# Avatar Imports
from werkzeug.security import safe_join
from PIL import Image
from io import BytesIO
import magic
from os import path


# Timestamp Imports
from datetime import datetime
from dateutil.parser import parse as parsedate
from email.utils import formatdate
from calendar import timegm

### helpers

def update_user_timestamp(user: User):
    user.last_updated = datetime.utcnow().replace(microsecond=0)
    return int(datetime.now().timestamp())

def is_valid_username(username: str):
    return re.match(pattern=r"^@[a-zA-Z0-9_]{1,40}@(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$", string=username)

### fmrl core routes

@app.route('/.well-known/fmrl/user/<username>/avatar', methods=['PUT'])
@httpauth.login_required
def update_user_avatar(username: str):

    # Request Validation
    user = User.query.filter_by(username=username).first()
    if user is None:
        return Response("No such user found.", 404)
    if user.username != httpauth.current_user().username:
        return Response("Unauthenticated.", 403)
    
    # Grab first chunk for MIME analysis
    file_size = 0
    chunk_size = 4096
    first_chunk = True
    image_bytes = BytesIO()
    chunk = request.stream.read(chunk_size)
    file_type = magic.from_buffer(chunk, mime=True)

    # Validate file magic
    if file_type not in app.config['ALLOWED_UPLOAD_TYPES']:
        return Response("Image not recognized as JPEG or PNG.", 400)

    # Read image into buffer and validate file size.
    while True:
        if first_chunk:
            image_bytes.write(chunk)
            first_chunk = False
        else:
            file_size += len(chunk)
            if file_size > app.config['UPLOAD_MAX_SIZE']:
                return Response("File too large.", 413)
            chunk = request.stream.read(chunk_size)
            if len(chunk) == 0:
                break
            image_bytes.write(chunk)
    
    img = Image.open(image_bytes)
    if img.height != img.width:
        return Response("Image must be square.", 400)
    
    # Stream buffer back to file on disk
    # TODO - Beef up security here
    with open(safe_join(app.config['AVATARS_DIR'], user.username), "bw") as file:
        file.write(image_bytes.getbuffer())

    # Update user and timestamp, return success
    user.avatar.original = "/.well-known/fmrl/avatars/{}".format(user.username)
    user.avatar.original_key = update_user_timestamp(user)
    db.session.commit()
    return Response("Success.", 200)

@app.route('/.well-known/fmrl/user/<username>', methods=['PATCH'])
@httpauth.login_required
def update_user_status(username: str):
    
    # Request Validation
    user = User.query.filter_by(username=username).first()
    if user is None:
        return Response("No such user found.", 404)
    if user.username != httpauth.current_user().username:
        return Response("Unauthenticated.", 403)
    
    # Schema Validation
    if not JsonLengthInputs(request).validate():
        return Response("Update field(s) too long!", 413)
    if not JsonTypeInputs(request).validate():
        return Response("Update fields not a valid type.", 400)
    
    # Semantic Validation
    update = {} 
    if request.json.get('avatar') is not None:
        return Response("Invalid endpoint for updating avatar.", 400)
    
    if request.json.get('emoji') is not None:
        if not request.json['emoji'] in EmojiSequence and request.json['emoji']:
            return Response("Invalid emoji.", 400)
        update['emoji'] = request.json['emoji']

    regex = re.compile('[\u0000-\u001F\u007F\u0080-\u009F]')
    for field in {"status", "media", "name"}:
        if request.json.get(field) is not None:
            if regex.search(request.json.get(field)) is not None:
                return Response("Invalid unicode character(s).", 400)
            update[field] = request.json[field]
    
    if request.json.get('media_type') is not None:
        update['media_type'] = request.json['media_type']

    if request.json.get('uri') is not None:
        if not is_valid_uri(request.json['uri']):
            return Response("Invalid URI.", 400)
        update['uri'] = normalize_uri(request.json['uri'])

    # Validation passed. Update user and times
    if update:
        for field in update:
            setattr(user.status_data, field, update[field])
        update_user_timestamp(user)
        db.session.commit()
    return Response("Success.", status=200)

@cross_origin()
@app.route('/.well-known/fmrl/users', methods=['GET'])
def get_user_statuses():
    # Basic request validation
    if not request.args.getlist('user'):
        return Response("Invalid request.", status=400)

    # If requested, send only updates newer than specified
    query_time = None
    if request.headers.get('If-Modified-Since') is not None:
        query_time = parsedate(request.headers['If-Modified-Since']).replace(tzinfo=None)
    
    users_list = []
    latest = None

    for username in set(request.args.getlist('user')):
        query = get_user_status(username, query_time)
        if query.headers.get('Last_modified') is not None:
            timestamp = parsedate(query.headers.get('Last-Modified')).replace(tzinfo=None)
            if latest is None or latest < timestamp:
                latest = timestamp
        
        if query.status_code == 200:
            # User exists. Return data normally.
            users_list.append({"username": username, "code": query.status_code, "data": query.get_json()})

        elif query.status_code == 304:
            # No change since last-modified. Return simple.
            users_list.append({"username": username, "code": query.status_code})

        else:
            # User doesn't exist or some other issue. Return fault.
            users_list.append({"username": username, "code": query.status_code, "msg": query.get_data(as_text=True)})
    return Response(json.dumps(users_list), status=200, mimetype='application/json')

def get_user_status(username: str, query_time=None):
    user = User.query.filter_by(username=username).first()
    if not user:
        # Return failed response (user doesn't exist)
        return Response("No such user found.", status=404)
    # If requested, send only updates newer than specified
    if request.headers.get('If-Modified-Since') is not None:
        query_time = parsedate(request.headers['If-Modified-Since']).replace(tzinfo=None)
    if query_time is not None and query_time >= user.last_updated:
        response = Response(None, status=304)
        response.headers['Last-Modified'] = formatdate(timeval=timegm(user.last_updated.timetuple()), localtime=False, usegmt=True)
        return response
    
    # Empty responses are valid, should return only values which are set
    user_status = {}
    if user.avatar.original is not None:
        user_status['avatar'] = {"original": "{}?{}".format(user.avatar.original, user.avatar.original_key)}
    for field in {"name", "status", "emoji", "media", "media_type", "uri"}:
        e = getattr(user.status_data, field)
        if e is not None:
            user_status[field] = e

    # Return successful response and user data
    response = Response(json.dumps(user_status), status=200, mimetype='application/json')
    response.headers['Last-Modified'] = formatdate(timeval=timegm(user.last_updated.timetuple()), localtime=False, usegmt=True)
    return response

### fmrl following routes

@app.route('/.well-known/fmrl/user/<username>/following', methods=['GET'])
@httpauth.login_required
def get_user_following(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return Response("No such user found.", status=404)
    if user.username != httpauth.current_user().username:
        return Response("Unauthenticated.", 403)
    user_follows = []
    if user.follows is not None:
        for follow in user.follows:
            user_follows.append(follow.username)
    return Response(json.dumps(user_follows), status=200, mimetype='application/json')

@app.route('/.well-known/fmrl/user/<username>/following', methods=['PATCH'])
@httpauth.login_required
def set_user_following(username: str):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return Response("No such user found.", status=404)
    if user.username != httpauth.current_user().username:
        return Response("Unauthenticated.", 403)
    
    success = False
    for action in {"add", "remove"}:
        if type(request.json.get(action)) is list:
            for name in request.json[action]:
                if not is_valid_username(name):
                    return Response("Invalid username(s).", 400)
                if action == "add":
                    success = True
                    if user.follows.filter_by(username=name).first() is None:
                        user.follows.append(UserFollow(username=name))
                else:
                    success = True
                    follow = user.follows.filter_by(username=name).first()
                    if follow is not None:
                        user.follows.remove(follow)
    if success:
        db.session.commit()
        return Response(None, status=200)
    else:
        return Response("Invalid request.", status=400)




    if type(request.json.get('add')) is list:
        for action in {"add", "remove"}:
            for name in request.json[action]:
                success = True

        for name in request.json['add']:
            success = True
            print(name)
    if type(request.json.get('remove')) is list:
        for name in request.json['remove']:
            success = True
            print(name)


### flashpaper routes

# TODO - Implement multiple resolution support
@cross_origin()
@app.route('/.well-known/fmrl/avatars/<username>', methods=['GET'])
def get_user_avatar(username: str):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return Response("No such user found.", status=404)
    image_path = safe_join(app.config['AVATARS_DIR'], username)
    if path.exists(image_path):
        mime_type = magic.from_file(image_path, mime=True)
        with open(image_path, "r") as image:
            return send_from_directory(app.config['AVATARS_DIR'], username, mimetype=mime_type)
    else:
        return Response("No such image found.", status=404)

### invalid routes

@app.route('/.well-known/fmrl/', defaults={'path': ''})
@app.route('/.well-known/fmrl/<path:path>')
def invalid_endpoint(path):
    return Response("Invalid API endpoint.", 405)
