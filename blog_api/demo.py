"""`flask --app app seed-demo` — fill an empty database with sample content.

Used by the hosted demo, whose database starts empty after every restart. It only seeds
when there are no users yet, so running it twice is harmless.
"""
import click
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import Article, Comment, Like, User

DEMO_PASSWORD = 'demo-password-123'

USERS = [
    ('ada', 'ada@example.com', 'Writes about engines that weave algebraic patterns.'),
    ('grace', 'grace@example.com', 'Compilers, COBOL and finding the first bug.'),
    ('alan', 'alan@example.com', 'Machines, morphogenesis and long-distance running.'),
]

ARTICLES = [
    ('ada', 'Notes on the Analytical Engine',
     'The engine might act upon other things besides number, were objects found whose mutual '
     'fundamental relations could be expressed by those of the abstract science of operations.'),
    ('grace', 'A short history of the compiler',
     'People said computers could only do arithmetic. A compiler is a program that writes '
     'programs — and it changed who could write software at all.'),
    ('alan', 'Can machines think?',
     'Instead of defining "think", ask a different question: can a machine imitate a person in '
     'conversation well enough that an interrogator cannot tell the difference?'),
    ('grace', 'Why I keep a nanosecond on my desk',
     'A nanosecond is the distance light travels in a billionth of a second — about thirty '
     'centimetres. Holding one makes latency something you can see.'),
]

COMMENTS = [
    (0, 'grace', 'The line between calculating and composing is thinner than people think.'),
    (0, 'alan', 'Lady Lovelace\'s objection deserves a whole article of its own.'),
    (1, 'ada', 'Writing programs that write programs — delightful.'),
    (2, 'ada', 'And what if the machine surprises us?'),
]

VOTES = [(0, 'grace', True), (0, 'alan', True), (1, 'ada', True), (2, 'grace', False), (2, 'ada', True)]


def seed():
    """Insert the sample content. Returns False if the database already had users."""
    if db.session.query(User.id).first() is not None:
        return False
    users = {}
    for username, email, bio in USERS:
        users[username] = User(username=username, email=email, bio=bio,
                               password=generate_password_hash(DEMO_PASSWORD))
        db.session.add(users[username])
    db.session.flush()
    articles = []
    for author, title, content in ARTICLES:
        article = Article(title=title, content=content, user_id=users[author].id)
        db.session.add(article)
        articles.append(article)
    db.session.flush()
    for index, author, content in COMMENTS:
        db.session.add(Comment(content=content, user_id=users[author].id, article_id=articles[index].id))
    for index, voter, is_like in VOTES:
        db.session.add(Like(user_id=users[voter].id, article_id=articles[index].id, is_like=is_like))
    db.session.commit()
    return True


def register_commands(app):
    @app.cli.command('seed-demo')
    def seed_demo_command():
        """Add sample users, articles, comments and votes to an empty database."""
        if seed():
            click.echo(f'Seeded demo data. Log in as ada@example.com / {DEMO_PASSWORD}')
        else:
            click.echo('Database already has users; nothing to seed.')
