"""Small, explicit request validation — no extra dependency needed for a handful of fields."""
import re

from flask import request

from .errors import ValidationError

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
USERNAME_RE = re.compile(r'^[A-Za-z0-9_.-]{3,30}$')


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError({'body': 'Send a JSON object with Content-Type: application/json.'})
    return data


def validate(data, rules, partial=False):
    """rules: {field: (type, checker)} where checker returns an error message or None.
    With partial=True (PATCH), missing fields are allowed but at least one must be present."""
    errors, clean = {}, {}
    for field, (kind, check) in rules.items():
        if field not in data or data[field] is None:
            if not partial:
                errors[field] = 'This field is required.'
            continue
        value = data[field]
        if kind is str and isinstance(value, str):
            value = value.strip()
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            errors[field] = f'Must be {"a string" if kind is str else "an integer" if kind is int else "a boolean"}.'
            continue
        message = check(value) if check else None
        if message:
            errors[field] = message
        else:
            clean[field] = value
    unknown = set(data) - set(rules)
    if partial and not clean and not errors:
        errors['body'] = f'Provide at least one of: {", ".join(rules)}.'
    if errors:
        raise ValidationError(errors)
    return clean, unknown


def length(min_len, max_len):
    def check(value):
        if len(value) < min_len:
            return 'This field cannot be empty.' if min_len == 1 else f'Must be at least {min_len} characters.'
        if len(value) > max_len:
            return f'Must be at most {max_len} characters.'
        return None
    return check


def email(value):
    if not EMAIL_RE.match(value) or len(value) > 150:
        return 'Must be a valid email address.'
    return None


def username(value):
    if not USERNAME_RE.match(value):
        return '3–30 characters: letters, digits, "_", "." or "-".'
    return None


def password(value):
    if len(value) < 8:
        return 'Must be at least 8 characters.'
    if len(value) > 128:
        return 'Must be at most 128 characters.'
    return None


def pagination(default_size, max_size):
    def as_int(name, default):
        raw = request.args.get(name, default)
        try:
            return int(raw)
        except (TypeError, ValueError):
            raise ValidationError({name: 'Must be an integer.'}, 'Invalid query parameter.')

    page = as_int('page', 1)
    per_page = as_int('per_page', default_size)
    errors = {}
    if page < 1:
        errors['page'] = 'Must be 1 or greater.'
    if not 1 <= per_page <= max_size:
        errors['per_page'] = f'Must be between 1 and {max_size}.'
    if errors:
        raise ValidationError(errors, 'Invalid query parameter.')
    return page, per_page
