"""One error format for the whole API:

    {"error": {"code": "validation_error", "message": "...", "details": {...}}}
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException

from .extensions import db


class APIError(Exception):
    def __init__(self, status, code, message, details=None, headers=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers or {}


class ValidationError(APIError):
    def __init__(self, details, message='The request body is invalid.'):
        super().__init__(400, 'validation_error', message, details)


class NotFound(APIError):
    def __init__(self, what='Resource'):
        super().__init__(404, 'not_found', f'{what} not found.')


class Unauthorized(APIError):
    def __init__(self, message='Authentication is required.'):
        super().__init__(401, 'unauthorized', message, headers={'WWW-Authenticate': 'Bearer'})


class Forbidden(APIError):
    def __init__(self, message='You are not allowed to do this.'):
        super().__init__(403, 'forbidden', message)


class Conflict(APIError):
    def __init__(self, message, details=None):
        super().__init__(409, 'conflict', message, details)


def error_response(status, code, message, details=None, headers=None):
    body = {'code': code, 'message': message}
    if details:
        body['details'] = details
    response = jsonify(error=body)
    response.status_code = status
    for key, value in (headers or {}).items():
        response.headers[key] = value
    return response


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err):
        db.session.rollback()
        return error_response(err.status, err.code, err.message, err.details, err.headers)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        code = (err.name or 'error').lower().replace(' ', '_')
        return error_response(err.code, code, err.description)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        app.logger.exception('Unhandled error')
        return error_response(500, 'internal_error', 'Something went wrong on our side.')
