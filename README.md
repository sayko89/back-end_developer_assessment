<p align="center">
  <img src="assets/hero.png" alt="Blog API — a RESTful backend for articles, comments and votes. Beside the title, a real POST /api/articles request and its 201 Created response." width="100%">
</p>

<p align="center">
  <a href="https://github.com/sayko89/back-end_developer_assessment/actions/workflows/tests.yml"><img src="https://github.com/sayko89/back-end_developer_assessment/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
</p>

<p align="center">
  <a href="#the-assignment">The assignment</a> &nbsp;·&nbsp;
  <a href="#endpoints">Endpoints</a> &nbsp;·&nbsp;
  <a href="#try-it-in-60-seconds">Try it</a> &nbsp;·&nbsp;
  <a href="#design">Design</a> &nbsp;·&nbsp;
  <a href="#then-and-now">Then and now</a>
</p>

<br>

A REST API for a small blog, built with **Flask**, **SQLAlchemy** and **JWT**. People can sign up, manage
their profile, publish and edit articles, comment, and like or dislike articles. Every endpoint is
documented in an **OpenAPI 3** reference with an interactive Swagger UI. It runs with one
`docker compose up`, its schema is versioned with **Alembic** migrations, and 43 tests run on **SQLite
and PostgreSQL** in GitHub Actions on every push.

<br>

## The assignment

This started as a take-home task for a back-end developer role at UniVision (June 2025). The brief asked
for three things — here is where each one lives:

| The brief asked for | Where it is |
|---|---|
| **Database design** for a blog (users, articles, comments …) in SQLite or PostgreSQL | [`models.py`](blog_api/models.py) — four tables, diagram [below](#data-model). Works on both databases; CI runs the tests on each. |
| **REST API**: article list / detail / create / update / delete | [`routes/articles.py`](blog_api/routes/articles.py) — with pagination, search and author filter |
| user registration, login and **profile management** | [`routes/auth.py`](blog_api/routes/auth.py), [`routes/users.py`](blog_api/routes/users.py) |
| adding and deleting **comments** | [`routes/comments.py`](blog_api/routes/comments.py) |
| simple **token-based authentication** | [`auth.py`](blog_api/auth.py) — JWT (HS256), `Authorization: Bearer <token>` |
| **Documentation** of the endpoints (Swagger / OpenAPI optional) | [`openapi.yaml`](blog_api/openapi.yaml), served as Swagger UI at **`/docs/`** |

Beyond the brief: like / dislike votes, one consistent error format, and the tests.

<br>

## Endpoints

All paths start with `/api`. 🔒 = needs `Authorization: Bearer <token>`.

| | Method | Path | What it does |
|---|---|---|---|
| **Auth** | `POST` | `/register` | Create an account |
| | `POST` | `/login` | Get a token (valid for 60 minutes) |
| **Profile** | `GET` | `/profile` 🔒 | Your profile |
| | `PATCH` | `/profile` 🔒 | Change username, bio, email or password¹ |
| | `DELETE` | `/profile` 🔒 | Delete your account and everything you posted¹ |
| | `GET` | `/users/{id}` | Someone's public profile (no email) |
| **Articles** | `GET` | `/articles` | List, newest first — `?page=`, `?per_page=`, `?author=`, `?q=` |
| | `GET` | `/articles/{id}` | One article with like, dislike and comment counts |
| | `POST` | `/articles` 🔒 | Publish |
| | `PUT` · `PATCH` | `/articles/{id}` 🔒 | Replace · partly update — author only |
| | `DELETE` | `/articles/{id}` 🔒 | Delete with its comments and votes — author only |
| **Votes** | `POST` | `/articles/{id}/like` 🔒 | `{"is_like": true}` likes, `false` dislikes; voting again changes your vote |
| | `DELETE` | `/articles/{id}/like` 🔒 | Take your vote back |
| **Comments** | `GET` | `/articles/{id}/comments` | List, oldest first, paginated |
| | `POST` | `/articles/{id}/comments` 🔒 | Comment |
| | `DELETE` | `/comments/{id}` 🔒 | Delete — the comment's author or the article's author |
| | `POST` | `/comments` 🔒 | Original v1 endpoint (article id in the body), kept for compatibility |

<sub>¹ Changing email or password, and deleting the account, require your current password. &nbsp; Also: <code>GET /health</code>.</sub>

<p align="center">
  <img src="assets/swagger.png" alt="Screenshot of the Swagger UI at /docs/ listing the Auth and Profile endpoints" width="100%">
</p>

<br>

## Try it in 60 seconds

**With Docker** — the API, PostgreSQL and the migrations, in one command:

```bash
git clone https://github.com/sayko89/back-end_developer_assessment.git
cd back-end_developer_assessment
docker compose up --build
```

Open **http://localhost:8000/docs/**. The container applies the database migrations before
starting the server (gunicorn).

**Without Docker** — Python 3.10+ and SQLite:

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app app db upgrade        # create the tables
flask --app app seed-demo         # optional: sample users, articles, comments and votes
flask --app app run
```

Open **http://127.0.0.1:5000/docs/** for the interactive reference, or use `curl`
(with Docker, use port `8000`):

```bash
# 1. sign up and log in
curl -s -X POST localhost:5000/api/register -H 'Content-Type: application/json' \
     -d '{"username":"ada","email":"ada@example.com","password":"correct-horse-battery"}'

TOKEN=$(curl -s -X POST localhost:5000/api/login -H 'Content-Type: application/json' \
     -d '{"email":"ada@example.com","password":"correct-horse-battery"}' | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')

# 2. publish, like and comment
curl -s -X POST localhost:5000/api/articles -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"title":"Hello","content":"My first post"}'
curl -s -X POST localhost:5000/api/articles/1/like -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"is_like":true}'
curl -s -X POST localhost:5000/api/articles/1/comments -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"content":"Nice!"}'

# 3. read it back
curl -s localhost:5000/api/articles
```

### Configuration

Everything is optional for local use; see [`.env.example`](.env.example).

| Variable | Default | |
|---|---|---|
| `SECRET_KEY` | random per process | Signs tokens. **Set it in production** — with the random default, tokens stop working after a restart. |
| `DATABASE_URL` | `sqlite:///blog.db` (in `./instance`) | For PostgreSQL: `postgresql://user:pass@host/db` and `pip install "psycopg[binary]"` |
| `TOKEN_TTL_MINUTES` | `60` | Token lifetime |
| `DEMO_SEED` | `0` | In Docker: `1` fills an empty database with sample content at startup |

### Deploy your own

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sayko89/back-end_developer_assessment)

[`render.yaml`](render.yaml) describes a free web service built from the `Dockerfile`, with a generated
`SECRET_KEY` and sample content. It deliberately uses SQLite: Render's free plan puts the service to sleep
after 15 idle minutes and resets its disk, so the demo starts fresh with sample data each time — and,
unlike Render's free PostgreSQL (which expires after 30 days), it never runs out. For a real deployment,
attach a PostgreSQL database and set `DATABASE_URL`.

### Schema changes

The schema is managed with **Alembic** (via Flask-Migrate) in [`migrations/`](migrations). After changing
a model:

```bash
flask --app app db migrate -m "describe the change"   # writes a new migration — review it
flask --app app db upgrade
```

A test applies the migrations to an empty database and fails if they don't match the models.

<br>

## Design

### Data model

```mermaid
erDiagram
    USER ||--o{ ARTICLE : writes
    USER ||--o{ COMMENT : writes
    USER ||--o{ LIKE : casts
    ARTICLE ||--o{ COMMENT : has
    ARTICLE ||--o{ LIKE : receives
    USER {
        int id PK
        string username UK
        string email UK
        string password "werkzeug hash"
        string bio
        datetime created_at
    }
    ARTICLE {
        int id PK
        string title
        text content
        int user_id FK
        datetime created_at
        datetime updated_at
    }
    COMMENT {
        int id PK
        text content
        int user_id FK
        int article_id FK
        datetime created_at
    }
    LIKE {
        int id PK
        int user_id FK
        int article_id FK
        bool is_like "true like, false dislike"
    }
```

- **One vote per person per article** is a database rule (`UNIQUE(user_id, article_id)`), not just an
  `if` in the code.
- Foreign keys use **`ON DELETE CASCADE`**, so deleting an article or an account removes what depends on
  it. SQLite only enforces this with `PRAGMA foreign_keys=ON`, which the app turns on for every connection.

### What happens to a request

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant A as token_required
    participant V as validate()
    participant H as Route handler
    participant D as Database
    C->>A: POST /api/articles + Bearer token
    A-->>C: 401 if missing, invalid or expired
    A->>V: user loaded into g.current_user
    V-->>C: 400 with a message per field
    V->>H: clean, trimmed values
    H->>D: insert, commit
    H-->>C: 201 + Location header + article JSON
```

### Decisions worth explaining

- **Errors have one shape** everywhere — including 404 and 405 from Flask itself:
  `{"error": {"code": "validation_error", "message": "…", "details": {"title": "This field cannot be empty."}}}`.
  A client needs one error handler, and validation errors say exactly which field is wrong.
- **401 vs 403.** 401 means "who are you?" (no token, bad token, wrong password); 403 means "I know who you
  are, but you can't do this" (editing someone else's article).
- **Login doesn't reveal which accounts exist** — a wrong email and a wrong password get the same answer.
- **No N+1 queries.** The article list fetches articles, authors, vote counts and comment counts in a
  single query with aggregated sub-queries, instead of two extra queries per article.
- **No hard-coded secret.** The key comes from `SECRET_KEY`; if it is missing the app uses a random one
  and warns, rather than a value that is public on GitHub.
- **Small dependency footprint.** Validation is a ~90-line module instead of a schema library — the API
  has only a handful of fields.

<br>

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

43 tests cover every endpoint: success paths, validation, permissions, expired and forged tokens,
cascading deletes and pagination. The migrations are applied to an empty database and compared with the
models, and the demo seed command is tested too. One test compares the Flask routes with `openapi.yaml`, so the
documentation can't drift out of date. GitHub Actions runs the suite on **Python 3.10 and 3.13**, each
against **SQLite and PostgreSQL 16**, with warnings treated as errors. A separate job builds the Docker
image, starts the whole `docker compose` stack and runs an end-to-end smoke test against it — including a
restart to check that data persists. To run the tests against PostgreSQL locally:

```bash
TEST_DATABASE_URL=postgresql://user:pass@localhost/blog_test python -m pytest
```

<br>

## Then and now

The version submitted for the assessment is preserved on the branch
[`original-submission`](https://github.com/sayko89/back-end_developer_assessment/tree/original-submission)
(the code was in `blog_backend.zip`). In October 2026 I reworked it. These problems in the original were
reproduced before fixing them:

| Original behaviour | Now |
|---|---|
| Code only inside a zip file; no `requirements.txt`, no tests | Browsable package, `requirements.txt`, 43 tests, CI |
| Swagger UI was enabled but listed **no endpoints** | Full OpenAPI 3 reference; a test keeps it in sync with the code |
| No profile management (part of the brief) | `GET` / `PATCH` / `DELETE /api/profile`, public `GET /api/users/{id}` |
| No way to list an article's comments | `GET /api/articles/{id}/comments` |
| Missing field or duplicate username → **500 Internal Server Error** | 400 with per-field messages; 409 for duplicates |
| Comments and votes accepted for **articles that don't exist** | 404 |
| Deleting an article left its comments and votes behind | Cascading deletes |
| `Authorization: Bearer <token>` rejected (only a bare token worked) | Bearer works; a bare token is still accepted |
| Missing token → 403 | 401 with `WWW-Authenticate: Bearer` |
| Secret key `'gizli-key'` hard-coded in three files; `debug=True` | `SECRET_KEY` from the environment; debug off by default |
| README said "SQLite or PostgreSQL", but the database was fixed to SQLite | `DATABASE_URL`, tested on both |
| Tables created with `create_all()` at import time | Versioned Alembic migrations, applied by the container on start |
| Ran only with `python app.py` and the Flask dev server | Docker image with gunicorn; `docker compose up` with PostgreSQL |

The URLs of the original endpoints still work.

### Not included (yet)

Honest limits of the current version: no refresh tokens or token revocation (logging out means
discarding the token), and no rate limiting on login attempts.

<br>

## Project structure

```text
app.py                  entry point:  flask --app app run
Dockerfile              python:3.13-slim + gunicorn, runs as a non-root user
docker-compose.yml      API + PostgreSQL 16
docker-entrypoint.sh    applies migrations (and optional demo data), then starts gunicorn
render.yaml             one-click demo deployment on Render
migrations/             Alembic migrations
blog_api/
  __init__.py           create_app() factory, blueprints, Swagger UI, SQLite foreign keys
  config.py             settings from environment variables
  models.py             User, Article, Comment, Like
  auth.py               JWT creation and @token_required
  validation.py         request validation and pagination
  errors.py             error classes and the single JSON error format
  openapi.yaml          API reference
  demo.py               `flask seed-demo` sample content
  routes/               auth · users · articles · comments
tests/                  pytest suite
tools/make_assets.py    renders the README images from the running app
```

<br>

---

<sub>Built with Flask, Flask-SQLAlchemy, Flask-Migrate, PyJWT, Flasgger and gunicorn. README images are rendered by
<a href="tools/make_assets.py"><code>tools/make_assets.py</code></a> from a real request to the API;
typefaces <a href="https://github.com/floriankarsten/space-grotesk">Space Grotesk</a> and
<a href="https://github.com/IBM/plex">IBM Plex</a> (SIL Open Font License, see <a href="tools/fonts"><code>tools/fonts</code></a>).
The assignment was set by UniVision; this repository is my own work and is not affiliated with the company.</sub>
