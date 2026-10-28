import re


def _flask_routes(app):
    routes = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static' or rule.endpoint.startswith('flasgger'):
            continue
        path = re.sub(r'<(?:\w+:)?(\w+)>', r'{\1}', rule.rule)
        for method in rule.methods - {'HEAD', 'OPTIONS'}:
            routes.add((path, method.lower()))
    return routes


def test_every_route_is_documented_and_nothing_else(app, client):
    spec = client.get('/apispec_1.json').get_json()
    documented = {(path, method) for path, ops in spec['paths'].items()
                  for method in ops if method != 'parameters'}
    assert documented == _flask_routes(app)


def test_swagger_ui_is_served(client):
    assert client.get('/docs/').status_code == 200


def test_health(client):
    assert client.get('/health').get_json() == {'status': 'ok'}


def test_unknown_route_uses_error_format(client):
    r = client.get('/api/does-not-exist')
    assert r.status_code == 404
    assert r.get_json()['error']['code'] == 'not_found'


def test_wrong_method_uses_error_format(client):
    r = client.delete('/api/articles')
    assert r.status_code == 405
    assert 'error' in r.get_json()
