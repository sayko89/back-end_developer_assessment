"""Blog API — a small RESTful backend for articles, comments and votes.

`create_app()` is an application factory, so the tests (and any deployment) can
build an app with their own configuration.
"""
import os

from flasgger import Swagger
from flask import Flask, jsonify
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import Config
from .errors import register_error_handlers
from .extensions import db, migrate

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
OPENAPI_FILE = os.path.join(PACKAGE_DIR, 'openapi.yaml')
MIGRATIONS_DIR = os.path.join(os.path.dirname(PACKAGE_DIR), 'migrations')


@event.listens_for(Engine, 'connect')
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores foreign keys unless asked; turn them on so ON DELETE CASCADE works."""
    if dbapi_connection.__class__.__module__.startswith('sqlite3'):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config())
    app.json.sort_keys = False  # keep fields in the order the API builds them
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    # render_as_batch lets Alembic alter tables on SQLite, which has limited ALTER TABLE support.
    migrate.init_app(app, db, directory=MIGRATIONS_DIR, render_as_batch=True)

    from .routes.articles import articles_bp
    from .routes.auth import auth_bp
    from .routes.comments import comments_bp
    from .routes.users import users_bp

    for bp in (auth_bp, users_bp, articles_bp, comments_bp):
        app.register_blueprint(bp, url_prefix='/api')

    register_error_handlers(app)

    from .demo import register_commands
    register_commands(app)

    app.config['SWAGGER'] = {'title': 'Blog API', 'openapi': '3.0.3', 'uiversion': 3,
                             'specs_route': '/docs/'}
    Swagger(app, template_file=OPENAPI_FILE, parse=False)

    @app.get('/health')
    def health():
        return jsonify(status='ok')

    # The schema is managed by Alembic migrations:  flask --app app db upgrade
    return app
