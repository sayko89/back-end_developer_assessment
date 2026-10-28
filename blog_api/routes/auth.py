from flask import Blueprint, current_app, jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import create_token
from ..errors import APIError, Conflict
from ..extensions import db
from ..models import User
from ..validation import email, json_body, length, password, username, validate

auth_bp = Blueprint('auth', __name__)


def ensure_unique(new_username=None, new_email=None, exclude_id=None):
    taken = {}
    if new_username is not None:
        q = User.query.filter(db.func.lower(User.username) == new_username.lower())
        if exclude_id:
            q = q.filter(User.id != exclude_id)
        if q.first():
            taken['username'] = 'This username is already taken.'
    if new_email is not None:
        q = User.query.filter(db.func.lower(User.email) == new_email.lower())
        if exclude_id:
            q = q.filter(User.id != exclude_id)
        if q.first():
            taken['email'] = 'This email is already registered.'
    if taken:
        raise Conflict('Username or email already in use.', taken)


@auth_bp.post('/register')
def register():
    data, _ = validate(json_body(), {
        'username': (str, username),
        'email': (str, email),
        'password': (str, password),
    })
    data['email'] = data['email'].lower()
    ensure_unique(data['username'], data['email'])
    user = User(username=data['username'], email=data['email'],
                password=generate_password_hash(data['password']))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:  # two requests raced past the check above
        db.session.rollback()
        raise Conflict('Username or email already in use.')
    return jsonify(user=user.private_dict()), 201


@auth_bp.post('/login')
def login():
    data, _ = validate(json_body(), {'email': (str, length(1, 150)), 'password': (str, length(1, 128))})
    user = User.query.filter(db.func.lower(User.email) == data['email'].lower()).first()
    # Same message whether the email or the password is wrong, so accounts can't be probed.
    if not user or not check_password_hash(user.password, data['password']):
        raise APIError(401, 'invalid_credentials', 'Email or password is incorrect.')
    ttl = current_app.config['TOKEN_TTL']
    return jsonify(token=create_token(user), token_type='Bearer',
                   expires_in=int(ttl.total_seconds()), user=user.private_dict())
