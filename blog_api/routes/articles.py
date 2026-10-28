from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import case, func

from ..auth import token_required
from ..errors import Forbidden, NotFound, ValidationError
from ..extensions import db
from ..models import Article, Comment, Like, User, iso
from ..validation import json_body, length, pagination, validate

articles_bp = Blueprint('articles', __name__)

ARTICLE_RULES = {'title': (str, length(1, 200)), 'content': (str, length(1, 20000))}


def _stats_query():
    """Articles with author and vote/comment counts in ONE query (no N+1)."""
    likes = (db.session.query(Like.article_id,
                              func.sum(case((Like.is_like.is_(True), 1), else_=0)).label('likes'),
                              func.sum(case((Like.is_like.is_(False), 1), else_=0)).label('dislikes'))
             .group_by(Like.article_id).subquery())
    comments = (db.session.query(Comment.article_id, func.count(Comment.id).label('comments'))
                .group_by(Comment.article_id).subquery())
    return (db.session.query(Article, User,
                             func.coalesce(likes.c.likes, 0), func.coalesce(likes.c.dislikes, 0),
                             func.coalesce(comments.c.comments, 0))
            .join(User, Article.user_id == User.id)
            .outerjoin(likes, likes.c.article_id == Article.id)
            .outerjoin(comments, comments.c.article_id == Article.id))


def _serialize(row, with_content=True):
    article, author, likes, dislikes, comment_count = row
    data = {
        'id': article.id,
        'title': article.title,
        'author': {'id': author.id, 'username': author.username},
        'likes': int(likes),
        'dislikes': int(dislikes),
        'comment_count': int(comment_count),
        'created_at': iso(article.created_at),
        'updated_at': iso(article.updated_at),
    }
    if with_content:
        data['content'] = article.content
    else:
        data['excerpt'] = article.content[:200] + ('…' if len(article.content) > 200 else '')
    return data


def _article_json(article_id):
    row = _stats_query().filter(Article.id == article_id).first()
    if row is None:
        raise NotFound('Article')
    return _serialize(row)


def _owned_article(article_id):
    article = db.session.get(Article, article_id)
    if article is None:
        raise NotFound('Article')
    if article.user_id != g.current_user.id:
        raise Forbidden('Only the author can change this article.')
    return article


@articles_bp.get('/articles')
def list_articles():
    cfg = current_app.config
    page, per_page = pagination(cfg['DEFAULT_PAGE_SIZE'], cfg['MAX_PAGE_SIZE'])
    query = _stats_query()
    if 'author' in request.args:
        try:
            query = query.filter(Article.user_id == int(request.args['author']))
        except ValueError:
            raise ValidationError({'author': 'Must be a user id.'}, 'Invalid query parameter.')
    search = request.args.get('q', '').strip()
    if search:
        pattern = f'%{search}%'
        query = query.filter(Article.title.ilike(pattern) | Article.content.ilike(pattern))
    total = query.count()
    rows = query.order_by(Article.created_at.desc(), Article.id.desc()) \
                .offset((page - 1) * per_page).limit(per_page).all()
    return jsonify(
        items=[_serialize(r, with_content=False) for r in rows],
        meta={'page': page, 'per_page': per_page, 'total': total,
              'pages': (total + per_page - 1) // per_page},
    )


@articles_bp.get('/articles/<int:article_id>')
def get_article(article_id):
    return jsonify(article=_article_json(article_id))


@articles_bp.post('/articles')
@token_required
def create_article():
    data, _ = validate(json_body(), ARTICLE_RULES)
    article = Article(title=data['title'], content=data['content'], user_id=g.current_user.id)
    db.session.add(article)
    db.session.commit()
    response = jsonify(article=_article_json(article.id))
    response.status_code = 201
    response.headers['Location'] = f'/api/articles/{article.id}'
    return response


@articles_bp.put('/articles/<int:article_id>')
@token_required
def replace_article(article_id):
    article = _owned_article(article_id)
    data, _ = validate(json_body(), ARTICLE_RULES)
    article.title, article.content = data['title'], data['content']
    db.session.commit()
    return jsonify(article=_article_json(article.id))


@articles_bp.patch('/articles/<int:article_id>')
@token_required
def update_article(article_id):
    article = _owned_article(article_id)
    data, _ = validate(json_body(), ARTICLE_RULES, partial=True)
    for field, value in data.items():
        setattr(article, field, value)
    db.session.commit()
    return jsonify(article=_article_json(article.id))


@articles_bp.delete('/articles/<int:article_id>')
@token_required
def delete_article(article_id):
    article = _owned_article(article_id)
    db.session.delete(article)  # its comments and votes are deleted with it
    db.session.commit()
    return '', 204


def _vote_counts(article_id):
    row = _stats_query().filter(Article.id == article_id).first()
    return {'likes': int(row[2]), 'dislikes': int(row[3])}


@articles_bp.post('/articles/<int:article_id>/like')
@token_required
def vote(article_id):
    if db.session.get(Article, article_id) is None:
        raise NotFound('Article')
    data, _ = validate(json_body(), {'is_like': (bool, None)})
    existing = Like.query.filter_by(user_id=g.current_user.id, article_id=article_id).first()
    if existing:
        existing.is_like = data['is_like']
    else:
        db.session.add(Like(user_id=g.current_user.id, article_id=article_id, is_like=data['is_like']))
    db.session.commit()
    return jsonify(your_vote='like' if data['is_like'] else 'dislike', **_vote_counts(article_id))


@articles_bp.delete('/articles/<int:article_id>/like')
@token_required
def remove_vote(article_id):
    if db.session.get(Article, article_id) is None:
        raise NotFound('Article')
    Like.query.filter_by(user_id=g.current_user.id, article_id=article_id).delete()
    db.session.commit()
    return jsonify(your_vote=None, **_vote_counts(article_id))
