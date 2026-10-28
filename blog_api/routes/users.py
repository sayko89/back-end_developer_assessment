from flask import Blueprint, g, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth import token_required
from ..errors import APIError, NotFound, ValidationError
from ..extensions import db
from ..models import Article, User
from ..validation import email, json_body, length, password, username, validate
from .auth import ensure_unique

users_bp = Blueprint('users', __name__)


@users_bp.get('/profile')
@token_required
def get_profile():
    return jsonify(user=g.current_user.private_dict())


@users_bp.patch('/profile')
@token_required
def update_profile():
    user = g.current_user
    body = json_body()
    data, _ = validate(body, {
        'username': (str, username),
        'email': (str, email),
        'bio': (str, length(0, 500)),
        'new_password': (str, password),
    }, partial=True)

    if 'new_password' in data or 'email' in data:
        # Changing credentials requires proving you know the current password.
        current = body.get('current_password')
        if not isinstance(current, str) or not check_password_hash(user.password, current):
            raise APIError(403, 'current_password_required',
                           'Changing your email or password requires your current_password.')

    if 'email' in data:
        data['email'] = data['email'].lower()
    ensure_unique(data.get('username'), data.get('email'), exclude_id=user.id)

    for field in ('username', 'email', 'bio'):
        if field in data:
            setattr(user, field, data[field])
    if 'new_password' in data:
        user.password = generate_password_hash(data['new_password'])
    db.session.commit()
    return jsonify(user=user.private_dict())


@users_bp.delete('/profile')
@token_required
def delete_profile():
    body = json_body()
    current = body.get('password')
    if not isinstance(current, str):
        raise ValidationError({'password': 'Confirm with your password to delete your account.'})
    if not check_password_hash(g.current_user.password, current):
        raise APIError(403, 'invalid_credentials', 'Password is incorrect.')
    db.session.delete(g.current_user)  # articles, comments and votes are removed with it
    db.session.commit()
    return '', 204


@users_bp.get('/users/<int:user_id>')
def get_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFound('User')
    article_count = db.session.query(db.func.count(Article.id)).filter(Article.user_id == user.id).scalar()
    return jsonify(user={**user.public_dict(), 'article_count': article_count})
