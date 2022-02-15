# Application Imports
from application import db, httpauth
from .models import JsonLengthInputs, JsonTypeInputs, User, UserFollow, UserWebhook
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

# Webhooks Imports
from urllib.parse import urlparse

### helpers
def is_valid_user(username: str):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return None
    return user

def is_authorized_user(request_username: str, auth_username: str):
    user = is_valid_user(request_username)
    if user is None or user.username != auth_username:
        return None
    return user

def is_modified(request_header: str, timestamp: datetime):
    if request_header is not None:
        return parsedate(request_header).replace(tzinfo=None) < timestamp
    return True

def unmodified_response(timestamp: datetime):
    response = Response(None, status=304)
    response.headers['Last-Modified'] = formatdate(timeval=timegm(timestamp.timetuple()), localtime=False, usegmt=True)
    return response

def invalid_request_response(error: str = "Invalid Request", code: int = 400):
    return Response(error, code)

def unauthorized_response():
    return Response("Unauthorized Access", status=401)

def missinguser_response():
    return Response("No such user", status=404)

def update_user_timestamp(user: User):
    user.last_updated = datetime.utcnow().replace(microsecond=0)
    return int(datetime.now().timestamp())

def is_valid_username(username: str):
    return re.match(pattern=r"^@[a-zA-Z0-9_]{1,40}@(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$", string=username)

### fmrl core routes

@app.route('/.well-known/fmrl/user/<username>/avatar', methods=['PUT'])
@httpauth.login_required
def update_user_avatar(username: str):
    user = is_authorized_user(username, httpauth.current_user().username)
    if user is None:
        return unauthorized_response()
        
    # Grab first chunk for MIME analysis
    file_size = 0
    chunk_size = 4096
    first_chunk = True
    image_bytes = BytesIO()
    chunk = request.stream.read(chunk_size)
    file_type = magic.from_buffer(chunk, mime=True)

    # Validate file magic
    if file_type not in app.config['ALLOWED_UPLOAD_TYPES']:
        return invalid_request_response("Image not recognized as JPEG or PNG")

    # Read image into buffer and validate file size.
    while True:
        if first_chunk:
            image_bytes.write(chunk)
            first_chunk = False
        else:
            file_size += len(chunk)
            if file_size > app.config['UPLOAD_MAX_SIZE']:
                return Response("File too large.", status=413)
            chunk = request.stream.read(chunk_size)
            if len(chunk) == 0:
                break
            image_bytes.write(chunk)
    
    img = Image.open(image_bytes)
    if img.height != img.width:
        return invalid_request_response("Image must be square")
    
    # Stream buffer back to file on disk
    # TODO - Beef up security here
    with open(safe_join(app.config['AVATARS_DIR'], user.username), "bw") as file:
        file.write(image_bytes.getbuffer())

    # Update user and timestamp, return success
    user.avatar.original = "/.well-known/fmrl/avatars/{}".format(user.username)
    user.avatar.original_key = update_user_timestamp(user)
    db.session.commit()
    return Response("Success.", status=200)

@app.route('/.well-known/fmrl/user/<username>', methods=['PATCH'])
@httpauth.login_required
def update_user_status(username: str):
    user = is_authorized_user(username, httpauth.current_user().username)
    if user is None:
        return unauthorized_response()
    
    # Schema Validation
    if not JsonLengthInputs(request).validate():
        return Response("Update field(s) too long!", status=413)
    if not JsonTypeInputs(request).validate():
        return invalid_request_response("Update fields not a valid type")
    
    # Semantic Validation
    update = {} 
    if request.json.get('avatar') is not None:
        return invalid_request_response("Invalid endpoint for updating avatar")
    
    if request.json.get('emoji') is not None:
        if not request.json['emoji'] in EmojiSequence and request.json['emoji']:
            return invalid_request_response("Invalid emoji")
        update['emoji'] = request.json['emoji']

    regex = re.compile('[\u0000-\u001F\u007F\u0080-\u009F]')
    for field in {"status", "media", "name"}:
        if request.json.get(field) is not None:
            if regex.search(request.json.get(field)) is not None:
                return invalid_request_response("Invalid unicode character(s)")
            update[field] = request.json[field]
    
    if request.json.get('media_type') is not None:
        update['media_type'] = request.json['media_type']

    if request.json.get('uri') is not None:
        if not is_valid_uri(request.json['uri']) or len(request.json['uri'].encode('utf-8')) > 500:
            return invalid_request_response("Invalid URI")
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
        return invalid_request_response()

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
    user = is_valid_user(username=username)
    if user is None:
        return missinguser_response()
    # If requested, send only updates newer than specified
    if query_time is not None and query_time >= user.last_updated:
        return unmodified_response(user.last_updated)
    
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
    user = is_authorized_user(username, httpauth.current_user().username)
    if user is None:
        return unauthorized_response()

    if not is_modified(request.headers.get('If-Modified-Since'), user.follows_updated):
        return unmodified_response(user.follows_updated)

    user_follows = []
    if user.follows is not None:
        for follow in user.follows:
            user_follows.append(follow.username)

    # Return successful response and user data
    response = Response(json.dumps(user_follows), status=200, mimetype='application/json')
    response.headers['Last-Modified'] = formatdate(timeval=timegm(user.follows_updated.timetuple()), localtime=False, usegmt=True)
    return response

@app.route('/.well-known/fmrl/user/<username>/following', methods=['PATCH'])
@httpauth.login_required
def set_user_following(username: str):
    user = is_authorized_user(username, httpauth.current_user().username)
    if user is None:
        return unauthorized_response()
    
    success = False
    for action in {"add", "remove"}:
        if type(request.json.get(action)) is list:
            for name in request.json[action]:
                if not is_valid_username(name):
                    return invalid_request_response("Invalid username(s)")
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
        user.follows_updated = datetime.utcnow().replace(microsecond=0)
        db.session.commit()
        return Response(None, status=200)
    else:
        return invalid_request_response()

### flashpaper routes

# TODO - Implement multiple resolution support
@cross_origin()
@app.route('/.well-known/fmrl/avatars/<username>', methods=['GET'])
def get_user_avatar(username: str):
    user = is_valid_user(username=username)
    if user is None:
        return missinguser_response()
    image_path = safe_join(app.config['AVATARS_DIR'], username)
    if path.exists(image_path):
        mime_type = magic.from_file(image_path, mime=True)
        with open(image_path, "r") as image:
            return send_from_directory(app.config['AVATARS_DIR'], username, mimetype=mime_type)
    else:
        return Response("No such image found.", status=404)

@app.route('/.well-known/fmrl/user/<username>/webhooks', methods=['POST'])
@httpauth.login_required
def add_user_webhook(username):
    user = is_authorized_user(username, httpauth.current_user().username)
    if user is None:
        return unauthorized_response()

    if not app.config['WEBHOOKS_ENABLED']:
        return invalid_request_response("Webhooks are not enabled", 403)
    
    if user.webhooks.count() >= app.config['MAX_WEBHOOKS']:
        return invalid_request_response("Already at maximum configured webhooks")
    
    if request.json.get('url') is not None:
        parsed_url = urlparse(request.json['url'])
        if parsed_url.scheme not in {"http", "https"}:
            return invalid_request_response("Webhooks must use HTTP or HTTPS")
        if parsed_url.username or parsed_url.password:
            return invalid_request_response("Webhooks must not contain credentials")
        if parsed_url.params or parsed_url.query or parsed_url.fragment:
            return invalid_request_response("Webhooks must not contain a parameter, querystring, or fragment")
    
    if request.json.get('method') is not None:
        if request.json['method'].upper() not in {"GET", "POST"}:
            return invalid_request_response("Method must be GET or POST")
    else:
        return invalid_request_response("Missing method")

    if user.webhooks.filter_by(url=parsed_url.geturl()).first() is None:
        user.webhooks.append(UserWebhook(url=parsed_url.geturl(), method=request.json['method'].upper()))
        db.session.commit()

    return Response("Success", status=200)

@app.route('/.well-known/fmrl/user/<username>/webhooks/<webhook_id>', methods=['DELETE'])
@httpauth.login_required
def delete_user_webhook(username, webhook_id):
    user = is_authorized_user(username, httpauth.current_user().username)
    if user is None:
        return unauthorized_response()

    if not app.config['WEBHOOKS_ENABLED']:
        return invalid_request_response("Webhooks are not enabled", 403)

    try:
        id = int(webhook_id)
    except (TypeError, ValueError):
        return invalid_request_response("Invalid or missing Webhook ID")
    
    webhook = user.webhooks.filter_by(id=id).first()
    if webhook is None:
        return invalid_request_response("Invalid or missing Webhook ID")
    user.webhooks.remove(webhook)
    db.session.commit()
    return Response(None, status=200)


@app.route('/.well-known/fmrl/user/<username>/webhooks', methods=['GET'])
@httpauth.login_required
def get_user_webhooks(username):
    user = is_authorized_user(username, httpauth.current_user().username)
    if user is None:
        return unauthorized_response()
    
    if not app.config['WEBHOOKS_ENABLED']:
        return invalid_request_response("Webhooks are not enabled", 403)

    user_webhooks = []
    if user.webhooks is not None:
        for webhook in user.webhooks:
            user_webhooks.append({"id": webhook.id, "url": webhook.url, "method": webhook.method})
    
    return Response(json.dumps(user_webhooks), status=200, mimetype='application/json')

### invalid routes

@app.route('/.well-known/fmrl/', defaults={'path': ''})
@app.route('/.well-known/fmrl/<path:path>')
def invalid_endpoint(path):
    return invalid_request_response("Invalid API endpoint", 405)
