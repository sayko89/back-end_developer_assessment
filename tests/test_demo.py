from blog_api.demo import DEMO_PASSWORD


def test_seed_demo_fills_an_empty_database_once(app, client):
    runner = app.test_cli_runner()
    first = runner.invoke(args=['seed-demo'])
    assert 'Seeded demo data' in first.output
    second = runner.invoke(args=['seed-demo'])
    assert 'nothing to seed' in second.output

    articles = client.get('/api/articles').get_json()
    assert articles['meta']['total'] == 4
    first_article = next(a for a in articles['items'] if a['title'] == 'Notes on the Analytical Engine')
    assert (first_article['likes'], first_article['comment_count']) == (2, 2)

    login = client.post('/api/login', json={'email': 'ada@example.com', 'password': DEMO_PASSWORD})
    assert login.status_code == 200
