# MindRepo

MindRepo is a private developer knowledge and recall system. It combines fast capture with structured long-form notes, references, revision history, and independent study cards; it is not a blogging platform.

## Status

Release candidate `0.1.0`: Levels 0–7 are implemented, including analytics, portable import/export, operational documentation, and production configuration. The final release audit and its environment gates are recorded in [docs/12-release-audit.md](docs/12-release-audit.md).

## Stack

- Python 3.12 (lockfile resolved with 3.12.13)
- Django 5.2.17 LTS (locked in `uv.lock`)
- SQLite locally; PostgreSQL in production
- Django Templates, HTMX, Alpine.js, Bootstrap 5, and custom CSS

## Languages

MindRepo supports English and Persian. Use the language selector in the desktop sidebar or mobile page header; the choice is saved in the Django language cookie. Persian switches the application shell to RTL while code and explicit technical content remain LTR.

## Dependency management

`pyproject.toml` is the single dependency declaration and `uv.lock` records resolved versions. Use `uv` when available; pip remains supported through the same file.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Setup

```powershell
git clone <repository-url>
cd MindRepo
uv sync --all-groups
Copy-Item .env.example .env
uv run python manage.py migrate
```

Pip alternative:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
python manage.py migrate
```

Unix-like shells use `source .venv/bin/activate` and `cp .env.example .env`.

## Environment

`.env` is optional for local startup because safe development defaults exist, but use it for local configuration. `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CSRF_TRUSTED_ORIGINS`, and `SECURE_SSL_REDIRECT` are supported. Production must set a real `SECRET_KEY`, non-empty `ALLOWED_HOSTS`, and a PostgreSQL `DATABASE_URL`.

## Database

Development defaults to `sqlite:///db.sqlite3`. Production settings require a PostgreSQL URL, for example `postgresql://mindrepo:password@localhost:5432/mindrepo`.

## Migrations

```powershell
uv run python manage.py makemigrations
uv run python manage.py migrate
```

## Create Superuser

```powershell
uv run python manage.py createsuperuser
```

## Run Development Server

```powershell
uv run python manage.py runserver
```

Open <http://127.0.0.1:8000/accounts/login/> and sign in with the superuser.

## PWA and offline behavior

Production enables the PWA service worker by default and requires HTTPS. Local development leaves registration off unless `PWA_ENABLED=True` is set in `.env`; browsers still treat localhost as a secure context for PWA testing. The worker caches only the named static application shell assets and `/offline/`. It does **not** persistently cache authenticated HTML, private concept content, JSON synchronization responses, or review pages.

Offline Knowledge is an explicit per-browser opt-in at `/settings/offline/`. It stores a structured private concept replica in IndexedDB for offline reading, local search, favorites, and Random Recall. Enable it only on a trusted device: IndexedDB is not encrypted by MindRepo. Logout and Clear Offline Data remove the local replica and queued changes. It is disabled by default in production with `OFFLINE_KNOWLEDGE_ENABLED=False` until the target-browser flow has been verified. See [docs/08-offline-and-sync.md](docs/08-offline-and-sync.md).

## Advanced knowledge

Concepts keep fast recall fields while supporting ordered Markdown sections, safe tables and code, self-hosted Mermaid diagrams, sources, technology/version context, freshness metadata, private attachments, and immutable content revisions. See [the advanced knowledge model](docs/13-advanced-knowledge-model.md).

## Reviews

Every concept receives a persistent default recall card, and optional custom cards have independent schedules. Open **Review** to work through overdue cards first, then currently due cards, then up to ten new cards per day. Archived custom cards preserve their schedule and history but leave the queue and mastery calculation. See [docs/06-review-system.md](docs/06-review-system.md).

## Discovery

Open `/search/` or use Ctrl/Cmd+K on desktop to search private concepts by title, alias, tag, category, or explanation. SQLite provides portable weighted matching; PostgreSQL adds full-text tie-breaking. Favorites are a lightweight `Concept.is_favorite` flag. Random Recall is casual and never changes a review schedule or writes a review log. See [docs/07-search-and-discovery.md](docs/07-search-and-discovery.md).

## Data portability and production

Open `/analytics/` for owner-scoped learning activity and `/settings/data/` to export JSON/Markdown or safely preview/import MindRepo JSON. See [data portability](docs/09-data-portability.md), [deployment](docs/10-production-deployment.md), and [backup/recovery](docs/11-backup-and-recovery.md). Production uses PostgreSQL, Gunicorn, Nginx, and HTTPS; `/health/` is a minimal liveness endpoint.

## Private attachments

Concepts can include private JPG, PNG, WEBP, GIF, PDF, TXT, and Markdown attachments up to 10 MB each. Files are stored under `MEDIA_ROOT` and served only by an authenticated owner-checked download view; do not configure Nginx to expose `MEDIA_ROOT` publicly. A complete production backup includes both PostgreSQL and the private attachment storage directory.

## Run Tests

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check
uv run python manage.py test
uv run ruff check .
uv lock --check
```

## Project layout

```text
config/                 Django settings and root URLs
apps/
  core/                 dashboard, shared layout, and error pages
  accounts/             custom user and authentication
  knowledge/            private category and concept knowledge domain
  reviews/              review state, scheduling, queue, and immutable history
  search/               private ranked search, command palette, favorites, and random recall
  offline/              opt-in sync protocol, change log, and offline mutation receipts
templates/              layouts and reusable includes
static/                 local Bootstrap, HTMX, Alpine, CSS, and JavaScript
docs/                   architecture and project rules
```

See [docs/01-architecture.md](docs/01-architecture.md) for boundaries and [docs/04-roadmap.md](docs/04-roadmap.md) for delivery order.

Production is expected to use PostgreSQL, Gunicorn, Nginx, and HTTPS. Docker is deliberately deferred until it solves a demonstrated deployment or onboarding problem.
