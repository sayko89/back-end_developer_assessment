import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog_api import create_app  # noqa: E402
from blog_api.config import TestConfig  # noqa: E402
from blog_api.extensions import db  # noqa: E402


@pytest.fixture
def app():
    """A fresh database for every test. Uses in-memory SQLite unless TEST_DATABASE_URL is set
    (CI also runs the suite against PostgreSQL)."""
    app = create_app(TestConfig())
    with app.app_context():
        db.create_all()  # fast path for tests; test_migrations.py checks the migrations separately
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


class Api:
    """Small helper so tests read like API calls."""

    def __init__(self, client):
        self.client = client

    def register(self, username='ada', email=None, password='password123'):
        email = email or f'{username}@example.com'
        return self.client.post('/api/register', json={'username': username, 'email': email, 'password': password})

    def login(self, email, password='password123'):
        return self.client.post('/api/login', json={'email': email, 'password': password})

    def user(self, username='ada', password='password123'):
        """Register and log in; return auth headers."""
        self.register(username, password=password)
        token = self.login(f'{username}@example.com', password).get_json()['token']
        return {'Authorization': f'Bearer {token}'}

    def article(self, headers, title='Hello', content='World'):
        r = self.client.post('/api/articles', headers=headers, json={'title': title, 'content': content})
        assert r.status_code == 201, r.get_json()
        return r.get_json()['article']


@pytest.fixture
def api(client):
    return Api(client)
