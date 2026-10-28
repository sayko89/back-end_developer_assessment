"""The other tests build the schema with create_all() for speed. These tests make sure the
Alembic migrations — what a real deployment runs — produce exactly the same schema."""
import os

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

from blog_api import create_app
from blog_api.config import TestConfig
from blog_api.extensions import db

TABLES = {'user', 'article', 'comment', 'like'}


@pytest.fixture
def empty_app(tmp_path):
    url = os.environ.get('TEST_DATABASE_URL') or f'sqlite:///{tmp_path / "migrations.db"}'
    app = create_app(TestConfig(database_url=url))
    with app.app_context():
        db.drop_all()
        with db.engine.begin() as conn:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
    yield app
    with app.app_context():
        db.drop_all()
        with db.engine.begin() as conn:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
        db.engine.dispose()


def test_upgrade_matches_the_models(empty_app):
    with empty_app.app_context():
        upgrade()
        assert TABLES <= set(inspect(db.engine).get_table_names())
        with db.engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), db.metadata)
        assert diff == [], f'Models and migrations differ — run `flask db migrate`: {diff}'


def test_downgrade_removes_everything(empty_app):
    with empty_app.app_context():
        upgrade()
        downgrade(revision='base')
        assert not TABLES & set(inspect(db.engine).get_table_names())


def test_app_works_on_a_migrated_database(empty_app):
    with empty_app.app_context():
        upgrade()
    client = empty_app.test_client()
    r = client.post('/api/register', json={'username': 'ada', 'email': 'ada@example.com',
                                           'password': 'password123'})
    assert r.status_code == 201
