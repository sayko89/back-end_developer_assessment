def test_comment_and_list(api, client):
    ada, bob = api.user('ada'), api.user('bob')
    article = api.article(ada)
    url = f"/api/articles/{article['id']}/comments"
    r = client.post(url, headers=bob, json={'content': 'First!'})
    assert r.status_code == 201
    comment = r.get_json()['comment']
    assert comment['author'] == {'id': 2, 'username': 'bob'}
    client.post(url, headers=ada, json={'content': 'Thanks'})

    body = client.get(url).get_json()
    assert [c['content'] for c in body['items']] == ['First!', 'Thanks']  # oldest first
    assert body['meta']['total'] == 2
    assert client.get(f"/api/articles/{article['id']}").get_json()['article']['comment_count'] == 2


def test_comment_validation(api, client):
    h = api.user('ada')
    url = f"/api/articles/{api.article(h)['id']}/comments"
    assert client.post(url, headers=h, json={'content': '   '}).status_code == 400
    assert client.post(url, headers=h, json={'content': 'x' * 2001}).status_code == 400


def test_cannot_comment_on_missing_article(api, client):
    h = api.user('ada')
    assert client.post('/api/articles/999/comments', headers=h, json={'content': 'Hi'}).status_code == 404
    assert client.get('/api/articles/999/comments').status_code == 404


def test_original_comment_endpoint_still_works(api, client):
    h = api.user('ada')
    article = api.article(h)
    r = client.post('/api/comments', headers=h, json={'content': 'Hi', 'article_id': article['id']})
    assert r.status_code == 201
    r = client.post('/api/comments', headers=h, json={'content': 'Hi', 'article_id': 999})
    assert r.status_code == 404


def test_who_can_delete_a_comment(api, client):
    ada, bob, cy = api.user('ada'), api.user('bob'), api.user('cyd')
    article = api.article(ada)
    url = f"/api/articles/{article['id']}/comments"
    first = client.post(url, headers=bob, json={'content': 'one'}).get_json()['comment']['id']
    second = client.post(url, headers=bob, json={'content': 'two'}).get_json()['comment']['id']

    assert client.delete(f'/api/comments/{first}', headers=cy).status_code == 403   # a stranger
    assert client.delete(f'/api/comments/{first}', headers=bob).status_code == 204  # its author
    assert client.delete(f'/api/comments/{second}', headers=ada).status_code == 204  # the article's author
    assert client.delete(f'/api/comments/{second}', headers=ada).status_code == 404
