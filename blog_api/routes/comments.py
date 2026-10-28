from flask import Blueprint, current_app, g, jsonify

from ..auth import token_required
from ..errors import Forbidden, NotFound
from ..extensions import db
from ..models import Article, Comment
from ..validation import json_body, length, pagination, validate

comments_bp = Blueprint('comments', __name__)


def _require_article(article_id):
    if db.session.get(Article, article_id) is None:
        raise NotFound('Article')


def _create(article_id, content):
    comment = Comment(content=content, user_id=g.current_user.id, article_id=article_id)
    db.session.add(comment)
    db.session.commit()
    response = jsonify(comment=comment.to_dict())
    response.status_code = 201
    return response


@comments_bp.get('/articles/<int:article_id>/comments')
def list_comments(article_id):
    _require_article(article_id)
    cfg = current_app.config
    page, per_page = pagination(cfg['DEFAULT_PAGE_SIZE'], cfg['MAX_PAGE_SIZE'])
    query = Comment.query.filter_by(article_id=article_id)
    total = query.count()
    comments = query.order_by(Comment.created_at.asc(), Comment.id.asc()) \
                    .offset((page - 1) * per_page).limit(per_page).all()
    return jsonify(items=[c.to_dict() for c in comments],
                   meta={'page': page, 'per_page': per_page, 'total': total,
                         'pages': (total + per_page - 1) // per_page})


@comments_bp.post('/articles/<int:article_id>/comments')
@token_required
def add_comment(article_id):
    _require_article(article_id)
    data, _ = validate(json_body(), {'content': (str, length(1, 2000))})
    return _create(article_id, data['content'])


@comments_bp.post('/comments')
@token_required
def add_comment_legacy():
    """Kept from the original version of the API: the article id is sent in the body."""
    data, _ = validate(json_body(), {'content': (str, length(1, 2000)), 'article_id': (int, None)})
    _require_article(data['article_id'])
    return _create(data['article_id'], data['content'])


@comments_bp.delete('/comments/<int:comment_id>')
@token_required
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        raise NotFound('Comment')
    # The comment's author can delete it, and so can the author of the article (moderation).
    if g.current_user.id not in (comment.user_id, comment.article.user_id):
        raise Forbidden('Only the comment author or the article author can delete this comment.')
    db.session.delete(comment)
    db.session.commit()
    return '', 204
