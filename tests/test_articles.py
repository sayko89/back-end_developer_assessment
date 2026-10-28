def test_create_and_get_article(api, client):
    h = api.user('ada')
    r = client.post('/api/articles', headers=h, json={'title': '  Hello  ', 'content': 'World'})
    assert r.status_code == 201
    article = r.get_json()['article']
    assert r.headers['Location'] == f"/api/articles/{article['id']}"
    assert article['title'] == 'Hello'  # surrounding whitespace is trimmed
    assert article['author'] == {'id': 1, 'username': 'ada'}
    assert (article['likes'], article['dislikes'], article['comment_count']) == (0, 0, 0)

    r = client.get(f"/api/articles/{article['id']}")
    assert r.get_json()['article']['content'] == 'World'


def test_article_validation(api, client):
    h = api.user('ada')
    r = client.post('/api/articles', headers=h, json={'title': '', 'content': 42})
    assert r.status_code == 400
    assert set(r.get_json()['error']['details']) == {'title', 'content'}
    r = client.post('/api/articles', headers=h, json={'title': 'x' * 201, 'content': 'ok'})
    assert r.status_code == 400


def test_missing_article_is_404(client):
    r = client.get('/api/articles/123')
    assert r.status_code == 404
    assert r.get_json()['error']['code'] == 'not_found'


def test_list_is_paginated_newest_first(api, client):
    h = api.user('ada')
    for i in range(12):
        api.article(h, title=f'Post {i}')
    r = client.get('/api/articles?per_page=5&page=1')
    body = r.get_json()
    assert body['meta'] == {'page': 1, 'per_page': 5, 'total': 12, 'pages': 3}
    assert [a['title'] for a in body['items']] == ['Post 11', 'Post 10', 'Post 9', 'Post 8', 'Post 7']
    assert 'content' not in body['items'][0] and 'excerpt' in body['items'][0]
    last = client.get('/api/articles?per_page=5&page=3').get_json()
    assert len(last['items']) == 2


def test_list_rejects_bad_pagination(client):
    assert client.get('/api/articles?page=0').status_code == 400
    assert client.get('/api/articles?per_page=500').status_code == 400
    assert client.get('/api/articles?page=abc').status_code == 400


def test_filter_by_author_and_search(api, client):
    ada, bob = api.user('ada'), api.user('bob')
    api.article(ada, title='Engines', content='analytical')
    api.article(bob, title='Compilers', content='COBOL history')
    by_bob = client.get('/api/articles?author=2').get_json()['items']
    assert [a['title'] for a in by_bob] == ['Compilers']
    found = client.get('/api/articles?q=cobol').get_json()['items']
    assert [a['title'] for a in found] == ['Compilers']


def test_only_the_author_can_edit_or_delete(api, client):
    ada, bob = api.user('ada'), api.user('bob')
    article = api.article(ada)
    url = f"/api/articles/{article['id']}"
    assert client.put(url, headers=bob, json={'title': 'x', 'content': 'y'}).status_code == 403
    assert client.patch(url, headers=bob, json={'title': 'x'}).status_code == 403
    assert client.delete(url, headers=bob).status_code == 403


def test_put_replaces_and_patch_updates(api, client):
    h = api.user('ada')
    article = api.article(h, title='Old', content='Old body')
    url = f"/api/articles/{article['id']}"
    r = client.put(url, headers=h, json={'title': 'New'})
    assert r.status_code == 400  # PUT needs every field
    r = client.patch(url, headers=h, json={'title': 'New'})
    assert r.get_json()['article']['title'] == 'New'
    assert r.get_json()['article']['content'] == 'Old body'
    r = client.put(url, headers=h, json={'title': 'Newer', 'content': 'New body'})
    assert r.get_json()['article']['content'] == 'New body'


def test_delete_article_removes_comments_and_votes(app, api, client):
    from blog_api.models import Comment, Like

    ada, bob = api.user('ada'), api.user('bob')
    article = api.article(ada)
    url = f"/api/articles/{article['id']}"
    client.post(url + '/comments', headers=bob, json={'content': 'Hi'})
    client.post(url + '/like', headers=bob, json={'is_like': True})
    assert client.delete(url, headers=ada).status_code == 204
    assert client.get(url).status_code == 404
    with app.app_context():
        assert Comment.query.count() == 0
        assert Like.query.count() == 0


def test_votes(api, client):
    ada, bob, cy = api.user('ada'), api.user('bob'), api.user('cyd')
    url = f"/api/articles/{api.article(ada)['id']}/like"
    assert client.post(url, headers=bob, json={'is_like': True}).get_json() == \
        {'your_vote': 'like', 'likes': 1, 'dislikes': 0}
    assert client.post(url, headers=cy, json={'is_like': False}).get_json()['dislikes'] == 1
    # voting again changes the vote instead of adding a second one
    assert client.post(url, headers=bob, json={'is_like': False}).get_json() == \
        {'your_vote': 'dislike', 'likes': 0, 'dislikes': 2}
    assert client.delete(url, headers=bob).get_json() == {'your_vote': None, 'likes': 0, 'dislikes': 1}


def test_vote_validation_and_missing_article(api, client):
    h = api.user('ada')
    url = f"/api/articles/{api.article(h)['id']}/like"
    assert client.post(url, headers=h, json={'is_like': 'yes'}).status_code == 400
    assert client.post(url, headers=h, json={}).status_code == 400
    assert client.post('/api/articles/999/like', headers=h, json={'is_like': True}).status_code == 404
