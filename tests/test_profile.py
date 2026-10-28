def test_get_own_profile(api, client):
    h = api.user('ada')
    r = client.get('/api/profile', headers=h)
    assert r.status_code == 200
    assert r.get_json()['user']['email'] == 'ada@example.com'


def test_update_username_and_bio(api, client):
    h = api.user('ada')
    r = client.patch('/api/profile', headers=h, json={'username': 'ada_l', 'bio': 'Hello'})
    assert r.status_code == 200
    user = r.get_json()['user']
    assert (user['username'], user['bio']) == ('ada_l', 'Hello')


def test_patch_needs_at_least_one_field(api, client):
    h = api.user('ada')
    r = client.patch('/api/profile', headers=h, json={})
    assert r.status_code == 400


def test_changing_password_requires_current_password(api, client):
    h = api.user('ada')
    r = client.patch('/api/profile', headers=h, json={'new_password': 'brand-new-pass'})
    assert r.status_code == 403
    r = client.patch('/api/profile', headers=h,
                     json={'new_password': 'brand-new-pass', 'current_password': 'password123'})
    assert r.status_code == 200
    assert api.login('ada@example.com', 'brand-new-pass').status_code == 200
    assert api.login('ada@example.com', 'password123').status_code == 401


def test_cannot_take_someone_elses_username(api, client):
    api.user('ada')
    h = api.user('bob')
    r = client.patch('/api/profile', headers=h, json={'username': 'ada'})
    assert r.status_code == 409


def test_public_profile_hides_email(api, client):
    h = api.user('ada')
    api.article(h)
    r = client.get('/api/users/1')
    user = r.get_json()['user']
    assert 'email' not in user
    assert user['article_count'] == 1
    assert client.get('/api/users/99').status_code == 404


def test_delete_account_removes_everything(api, client):
    ada = api.user('ada')
    bob = api.user('bob')
    article = api.article(ada)
    client.post(f"/api/articles/{article['id']}/comments", headers=bob, json={'content': 'Nice'})
    client.post(f"/api/articles/{article['id']}/like", headers=bob, json={'is_like': True})

    assert client.delete('/api/profile', headers=ada, json={'password': 'wrong'}).status_code == 403
    assert client.delete('/api/profile', headers=ada, json={'password': 'password123'}).status_code == 204

    assert client.get(f"/api/articles/{article['id']}").status_code == 404
    assert client.get('/api/profile', headers=ada).status_code == 401  # token of a deleted account
    assert client.get('/api/profile', headers=bob).status_code == 200
