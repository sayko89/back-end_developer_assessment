import os
import secrets
import warnings
from datetime import timedelta


def _normalize(url):
    # Accept the common "postgres://" / "postgresql://" forms and use the psycopg 3 driver.
    for prefix in ('postgres://', 'postgresql://'):
        if url.startswith(prefix):
            url = 'postgresql+psycopg://' + url[len(prefix):]
    return url


class Config:
    """Settings come from environment variables (see .env.example)."""

    def __init__(self):
        self.SQLALCHEMY_DATABASE_URI = _normalize(os.environ.get('DATABASE_URL') or 'sqlite:///blog.db')
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.TOKEN_TTL = timedelta(minutes=int(os.environ.get('TOKEN_TTL_MINUTES', '60')))
        self.DEFAULT_PAGE_SIZE = 10
        self.MAX_PAGE_SIZE = 50

        secret = os.environ.get('SECRET_KEY')
        if not secret:
            # Never fall back to a hard-coded key. A random key is safe; its only cost is that
            # tokens stop working when the server restarts.
            warnings.warn('SECRET_KEY is not set; using a random key for this process. '
                          'Set SECRET_KEY in production.', RuntimeWarning, stacklevel=2)
            secret = secrets.token_hex(32)
        self.SECRET_KEY = secret


class TestConfig(Config):
    __test__ = False  # not a pytest test class, despite the name

    def __init__(self, database_url=None):
        os.environ.setdefault('SECRET_KEY', 'test-secret-key-that-is-at-least-32-bytes-long')
        super().__init__()
        self.TESTING = True
        self.SQLALCHEMY_DATABASE_URI = _normalize(database_url or os.environ.get('TEST_DATABASE_URL') or 'sqlite://')
