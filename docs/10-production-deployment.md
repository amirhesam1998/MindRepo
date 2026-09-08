# Production deployment

MindRepo is one Django process behind Gunicorn and Nginx, with PostgreSQL and HTTPS. Use `deploy/gunicorn.conf.py`, `deploy/nginx/mindrepo.conf.example`, and `deploy/systemd/mindrepo.service.example` as placeholders, not copy-paste production credentials.

1. Configure `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CSRF_TRUSTED_ORIGINS`, `CACHE_LOCATION`, `OFFLINE_KNOWLEDGE_ENABLED=False`, and `DJANGO_SETTINGS_MODULE=config.settings.production`.
2. Run `uv sync --all-groups`, `uv run python manage.py migrate`, `uv run python manage.py collectstatic`, and `uv run python manage.py check --deploy`.
3. Start Gunicorn, configure Nginx TLS, then confirm `/health/`, login, search, review, and static assets.

Production requires PostgreSQL and HTTPS. Nginx is the trusted TLS proxy assumed by `SECURE_PROXY_SSL_HEADER`; do not expose Gunicorn directly. The file cache at `CACHE_LOCATION` is shared by local Gunicorn workers on one host; use a shared cache or document best-effort throttling before multi-host deployment. The CI workflow defines SQLite plus PostgreSQL coverage, but release approval requires evidence that the PostgreSQL job actually passed.
