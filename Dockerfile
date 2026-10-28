FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes don't invalidate this layer
COPY requirements.txt .
RUN pip install -r requirements.txt "psycopg[binary]>=3.1,<4" "gunicorn>=22,<24"

COPY app.py docker-entrypoint.sh ./
COPY blog_api ./blog_api
COPY migrations ./migrations

# Don't run as root
RUN useradd --create-home --uid 10001 app && chown -R app /app && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=2)"

ENTRYPOINT ["./docker-entrypoint.sh"]
