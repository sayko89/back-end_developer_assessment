"""Render the images used in the README.

    assets/hero.png      Title card with a real request/response captured from the API
    assets/swagger.png   Screenshot of the live Swagger UI served at /docs/

Everything shown is produced by the running application — the request in the hero is
actually sent, and the response is what the API returned.

Requirements (only for regenerating images): the packages in requirements.txt and
Playwright with Chromium (`pip install playwright && playwright install chromium`).

    python tools/make_assets.py
"""
import base64
import html
import json
import os
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, 'assets')
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'asset-rendering-secret-key-0123456789abcdef')

from playwright.sync_api import sync_playwright  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from blog_api import create_app  # noqa: E402
from blog_api.config import TestConfig  # noqa: E402

PAPER, INK, SIGNAL = '#F3F0E8', '#121212', '#E4572E'


def _b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


def font_css():
    faces = [('Grotesk', 'SpaceGrotesk-Medium.woff2', 500), ('Grotesk', 'SpaceGrotesk-Bold.woff2', 700),
             ('Mono', 'IBMPlexMono-Regular.woff2', 400), ('Mono', 'IBMPlexMono-SemiBold.woff2', 600),
             ('Sans', 'IBMPlexSans-Regular.woff2', 400)]
    return '\n'.join(
        f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
        f"src: url('data:font/woff2;base64,{_b64(os.path.join(TOOLS, 'fonts', file))}') format('woff2'); }}"
        for family, file, weight in faces)


def capture_exchange(app):
    """Register, log in and create an article — return the real request and response."""
    client = app.test_client()
    client.post('/api/register', json={'username': 'ada', 'email': 'ada@example.com',
                                       'password': 'correct-horse-battery'})
    token = client.post('/api/login', json={'email': 'ada@example.com',
                                            'password': 'correct-horse-battery'}).get_json()['token']
    body = {'title': 'Notes on the Analytical Engine', 'content': 'The engine weaves algebraic patterns…'}
    r = client.post('/api/articles', json=body, headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 201
    return token, body, r


def json_html(value, indent=0):
    """Pretty-print JSON as HTML with quiet syntax colours."""
    pad = '  ' * indent
    if isinstance(value, dict):
        items = [f'{pad}  <span class="k">"{html.escape(k)}"</span>: {json_html(v, indent + 1).lstrip()}'
                 for k, v in value.items()]
        return pad + '{\n' + ',\n'.join(items) + '\n' + pad + '}'
    if isinstance(value, str):
        return pad + f'<span class="s">{html.escape(json.dumps(value, ensure_ascii=False))}</span>'
    return pad + f'<span class="n">{html.escape(json.dumps(value))}</span>'


def hero_html(token, body, response, stats):
    article = response.get_json()['article']
    shown = {'article': {k: article[k] for k in ('id', 'title', 'author', 'likes', 'created_at')}}
    req_body = json_html(body)
    res_body = json_html(shown)
    token_short = token[:18] + '…'
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_css()}
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1280px; height: 640px; background: {PAPER}; color: {INK}; font-family: 'Sans'; position: relative; overflow: hidden; }}
.left {{ position: absolute; left: 72px; top: 64px; width: 560px; }}
.kicker {{ font-family: 'Mono'; font-weight: 600; font-size: 13px; letter-spacing: .16em; text-transform: uppercase; }}
.kicker b {{ color: {SIGNAL}; }}
h1 {{ font-family: 'Grotesk'; font-weight: 700; font-size: 128px; letter-spacing: -.045em; line-height: .9; margin-top: 34px; }}
h1 span {{ color: {SIGNAL}; }}
.sub {{ font-size: 25px; line-height: 1.38; margin-top: 26px; color: #2b2b2b; }}
.stack {{ font-family: 'Mono'; font-size: 15px; margin-top: 22px; color: #555; }}
.stats {{ position: absolute; left: 72px; bottom: 56px; width: 560px; display: flex; border-top: 2px solid {INK}; }}
.stat {{ flex: 1; padding-top: 14px; }}
.stat .num {{ font-family: 'Grotesk'; font-weight: 700; font-size: 44px; letter-spacing: -.03em; }}
.stat .lbl {{ font-family: 'Mono'; font-size: 12.5px; text-transform: uppercase; letter-spacing: .12em; color: #555; margin-top: 2px; }}
.card {{ position: absolute; right: 64px; top: 56px; width: 536px; bottom: 56px; background: {INK}; color: #ECE8DF;
         font-family: 'Mono'; font-size: 14px; line-height: 1.4; padding: 22px 30px; }}
.label {{ font-size: 11.5px; letter-spacing: .16em; text-transform: uppercase; color: #8d8a83; margin-bottom: 8px; }}
.line {{ white-space: pre; }}
.method {{ color: {SIGNAL}; font-weight: 600; }}
.hdr {{ color: #a9a59c; }}
.k {{ color: #b9b4a8; }} .s {{ color: #ECE8DF; }} .n {{ color: {SIGNAL}; }}
.status {{ font-weight: 600; }}
.status i {{ font-style: normal; color: {INK}; background: {SIGNAL}; padding: 1px 7px; margin-right: 8px; }}
.rule {{ border-top: 1px dashed #3a3a3a; margin: 18px 0 16px; }}
pre {{ font-family: 'Mono'; margin: 8px 0 0; white-space: pre; }}
</style></head><body>
<div class="left">
  <div class="kicker"><b>■</b>&nbsp; Take-home assessment &nbsp;·&nbsp; UniVision &nbsp;·&nbsp; 2025</div>
  <h1>Blog API<span>.</span></h1>
  <div class="sub">A RESTful backend for articles, comments and votes — with accounts, token auth and an OpenAPI reference.</div>
  <div class="stack">Python · Flask · SQLAlchemy · JWT · OpenAPI 3</div>
</div>
<div class="stats">
  <div class="stat"><div class="num">{stats['endpoints']}</div><div class="lbl">endpoints</div></div>
  <div class="stat"><div class="num">{stats['tests']}</div><div class="lbl">tests</div></div>
  <div class="stat"><div class="num">2</div><div class="lbl">databases · CI</div></div>
</div>
<div class="card">
  <div class="label">Request</div>
  <div class="line"><span class="method">POST</span> /api/articles</div>
  <div class="line hdr">Authorization: Bearer {html.escape(token_short)}</div>
  <pre>{req_body}</pre>
  <div class="rule"></div>
  <div class="label">Response — captured from the running API</div>
  <div class="line status"><i>201</i>Created</div>
  <div class="line hdr">Location: {html.escape(response.headers['Location'])}</div>
  <pre>{res_body}</pre>
</div>
</body></html>"""


def count_stats(app):
    endpoints = {(r.rule, m) for r in app.url_map.iter_rules()
                 if not r.endpoint.startswith(('flasgger', 'static'))
                 for m in r.methods - {'HEAD', 'OPTIONS'}}
    tests = 0
    for name in os.listdir(os.path.join(ROOT, 'tests')):
        if name.startswith('test_') and name.endswith('.py'):
            with open(os.path.join(ROOT, 'tests', name)) as f:
                tests += sum(1 for line in f if line.startswith('def test_'))
    return {'endpoints': len(endpoints), 'tests': tests}


def swagger_plate_html(screenshot):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_css()}
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1280px; background: {PAPER}; color: {INK}; padding: 48px 64px 56px; font-family: 'Sans'; }}
.top {{ display: flex; justify-content: space-between; align-items: baseline; border-bottom: 2px solid {INK}; padding-bottom: 12px; }}
.kicker {{ font-family: 'Mono'; font-weight: 600; font-size: 13px; letter-spacing: .16em; text-transform: uppercase; }}
.kicker b {{ color: {SIGNAL}; }}
.cap {{ font-family: 'Mono'; font-size: 13px; color: #555; }}
img {{ display: block; width: 100%; margin-top: 24px; border: 2px solid {INK}; }}
</style></head><body>
<div class="top"><div class="kicker"><b>■</b>&nbsp; Interactive reference &nbsp;·&nbsp; GET /docs/</div>
<div class="cap">Screenshot of the running app · OpenAPI 3.0.3</div></div>
<img src="data:image/png;base64,{_b64(screenshot)}">
</body></html>"""


def main():
    os.makedirs(ASSETS, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(TestConfig(database_url=f'sqlite:///{os.path.join(tmp, "demo.db")}'))
        token, body, response = capture_exchange(app)
        stats = count_stats(app)

        server = make_server('127.0.0.1', 0, app)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_port

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1280, 'height': 640}, device_scale_factor=2)
            page.set_content(hero_html(token, body, response, stats))
            page.wait_for_timeout(300)
            page.screenshot(path=os.path.join(ASSETS, 'hero.png'))

            ui = browser.new_page(viewport={'width': 1200, 'height': 980}, device_scale_factor=1)
            ui.goto(f'http://127.0.0.1:{port}/docs/')
            ui.wait_for_selector('.opblock', timeout=15000)
            ui.wait_for_timeout(500)
            shot = os.path.join(tmp, 'swagger-raw.png')
            ui.screenshot(path=shot, clip={'x': 0, 'y': 0, 'width': 1200, 'height': 980})

            plate = browser.new_page(viewport={'width': 1280, 'height': 400}, device_scale_factor=1)
            plate.set_content(swagger_plate_html(shot))
            plate.wait_for_timeout(300)
            plate.screenshot(path=os.path.join(ASSETS, 'swagger.png'), full_page=True)
            browser.close()
        server.shutdown()

    for name in ('hero.png', 'swagger.png'):
        path = os.path.join(ASSETS, name)
        print(f'wrote assets/{name} ({os.path.getsize(path) // 1024} KB)')


if __name__ == '__main__':
    main()
