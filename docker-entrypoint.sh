#!/bin/sh
# Bring the database schema up to date, then start the server.
# Any arguments replace the default command, e.g.:  docker compose run api flask --app app db current
set -e

# Without SECRET_KEY each gunicorn worker would invent its own key, and a token issued by one
# worker would be rejected by another. Generate one key here, shared by all workers.
if [ -z "${SECRET_KEY:-}" ]; then
  echo "SECRET_KEY is not set; generating a temporary one (tokens reset when the container restarts)." >&2
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
  export SECRET_KEY
fi

flask --app app db upgrade

# The hosted demo starts with an empty database; fill it with sample content.
if [ "${DEMO_SEED:-0}" = "1" ]; then
  flask --app app seed-demo
fi

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Hosting platforms such as Render pass the port in $PORT.
exec gunicorn --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --access-logfile - app:app
