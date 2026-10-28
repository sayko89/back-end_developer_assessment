from datetime import datetime, timedelta, timezone

import jwt


def test_register_returns_user_without_password(api):
    r = api.register('ada')
    assert r.status_code == 201
    user = r.get_json()['user']
    assert user['username'] == 'ada'
    assert user['email'] == 'ada@example.com'
    assert 'password' not in user


def test_register_validates_input(client):
    r = client.post('/api/register', json={'email': 'not-an-email', 'password': 'short'})
    assert r.status_code == 400
    details = r.get_json()['error']['details']
    assert set(details) == {'username', 'email', 'password'}


def test_register_rejects_non_json(client):
    r = client.post('/api/register', data='hello', content_type='text/plain')
    assert r.status_code == 400
    assert r.get_json()['error']['code'] == 'validation_error'


def test_duplicate_username_and_email_are_conflicts(api):
    api.register('ada')
    r = api.register('ada', email='other@example.com')
    assert r.status_code == 409
    assert 'username' in r.get_json()['error']['details']
    r = api.register('ADA_2', email='ADA@example.com')  # emails are case-insensitive
    assert r.status_code == 409
    assert 'email' in r.get_json()['error']['details']


def test_login_returns_bearer_token(api):
    api.register('ada')
    r = api.login('ada@example.com')
    assert r.status_code == 200
    body = r.get_json()
    assert body['token_type'] == 'Bearer'
    assert body['expires_in'] == 3600
    assert body['user']['username'] == 'ada'


def test_login_with_wrong_password_or_unknown_email(api):
    api.register('ada')
    wrong = api.login('ada@example.com', 'wrong-password')
    unknown = api.login('nobody@example.com')
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()  # no hint about which part was wrong


def test_protected_endpoint_requires_token(client):
    r = client.post('/api/articles', json={'title': 't', 'content': 'c'})
    assert r.status_code == 401
    assert r.headers['WWW-Authenticate'] == 'Bearer'


def test_invalid_token(client):
    r = client.get('/api/profile', headers={'Authorization': 'Bearer not-a-jwt'})
    assert r.status_code == 401
    assert r.get_json()['error']['message'] == 'Token is invalid.'


def test_expired_token(app, api, client):
    api.register('ada')
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token = jwt.encode({'sub': '1', 'iat': past, 'exp': past + timedelta(hours=1)},
                       app.config['SECRET_KEY'], algorithm='HS256')
    r = client.get('/api/profile', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 401
    assert 'expired' in r.get_json()['error']['message']


def test_token_signed_with_another_key_is_rejected(api, client):
    api.register('ada')
    token = jwt.encode({'sub': '1', 'exp': datetime.now(timezone.utc) + timedelta(hours=1)},
                       'some-other-secret-key-of-sufficient-length', algorithm='HS256')
    r = client.get('/api/profile', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 401


def test_bare_token_still_accepted_for_backwards_compatibility(api, client):
    api.register('ada')
    token = api.login('ada@example.com').get_json()['token']
    r = client.get('/api/profile', headers={'Authorization': token})
    assert r.status_code == 200
