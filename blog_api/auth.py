"""JWT helpers and the @token_required decorator."""
from datetime import datetime, timezone
from functools import wraps

import jwt
from flask import current_app, g, request

from .errors import Unauthorized
from .extensions import db
from .models import User


def create_token(user):
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user.id), 'iat': now, 'exp': now + current_app.config['TOKEN_TTL']}
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def _token_from_header():
    header = request.headers.get('Authorization', '').strip()
    if not header:
        raise Unauthorized('Missing Authorization header. Use: Authorization: Bearer <token>')
    scheme, _, token = header.partition(' ')
    if scheme.lower() == 'bearer' and token:
        return token.strip()
    if not token:  # a bare token, as accepted by the original version of this API
        return header
    raise Unauthorized('Unsupported Authorization scheme. Use: Authorization: Bearer <token>')


def token_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _token_from_header()
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'],
                                 options={'require': ['sub', 'exp']})
        except jwt.ExpiredSignatureError:
            raise Unauthorized('Token has expired. Log in again.')
        except jwt.InvalidTokenError:
            raise Unauthorized('Token is invalid.')
        user = db.session.get(User, int(payload['sub'])) if payload['sub'].isdigit() else None
        if user is None:
            raise Unauthorized('The account for this token no longer exists.')
        g.current_user = user
        return view(*args, **kwargs)
    return wrapper
