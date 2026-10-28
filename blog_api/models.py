from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    """ISO 8601 in UTC. SQLite drops the timezone, so naive values are treated as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)  # password hash, never the password
    bio = db.Column(db.String(500), nullable=False, default='')
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    articles = db.relationship('Article', backref='author', lazy=True,
                               cascade='all, delete-orphan', passive_deletes=True)
    comments = db.relationship('Comment', backref='user', lazy=True,
                               cascade='all, delete-orphan', passive_deletes=True)
    likes = db.relationship('Like', backref='user', lazy=True,
                            cascade='all, delete-orphan', passive_deletes=True)

    def public_dict(self):
        return {'id': self.id, 'username': self.username, 'bio': self.bio,
                'created_at': iso(self.created_at)}

    def private_dict(self):
        return {**self.public_dict(), 'email': self.email}


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    comments = db.relationship('Comment', backref='article', lazy=True,
                               cascade='all, delete-orphan', passive_deletes=True)
    likes = db.relationship('Like', backref='article', lazy=True,
                            cascade='all, delete-orphan', passive_deletes=True)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id', ondelete='CASCADE'), nullable=False, index=True)

    def to_dict(self):
        return {'id': self.id, 'content': self.content, 'article_id': self.article_id,
                'author': {'id': self.user.id, 'username': self.user.username},
                'created_at': iso(self.created_at)}


class Like(db.Model):
    """A vote on an article: is_like=True is a like, False a dislike. One vote per user per article."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id', ondelete='CASCADE'), nullable=False, index=True)
    is_like = db.Column(db.Boolean, nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'article_id', name='unique_user_article'),)
