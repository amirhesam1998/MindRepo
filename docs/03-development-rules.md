# Development rules

## Before every level

Inspect the repository, these documents, models and migrations, URLs, templates, and tests before changing code. Preserve working behavior, reuse established patterns, and make schema changes only through migrations.

## Code conventions

- Prefer Django and Python standard-library features. Add the smallest dependency only for a concrete unmet need.
- Use clear names, PEP 8, useful type hints, small functions, and 100-column Python lines.
- Keep simple CRUD in forms, models, and views. Put multi-record transactions and algorithms in app-local services.
- Use Django forms and messages. Validate trust-boundary input server-side.
- Reusable template fragments belong in includes; templates may format, not decide business rules.
- Prefer HTMX over custom JavaScript. Alpine behavior is small and locally scoped; avoid global scripts.
- Use mobile-first CSS, semantic CSS variables, logical properties, and accessible HTML. Code is always LTR.

## Security and ownership

Use the custom user model from the first migration. Every private query scopes by `owner=request.user`; never accept an owner ID from the request. Detail, edit, delete, relation, review, and search endpoints must verify ownership before returning data or mutating it. Keep CSRF protection enabled, rely on Django escaping by default, validate forms, and sanitize any future rich HTML. Review ratings additionally submit the rendered state version; the service locks the row and rejects stale submissions rather than overwriting newer schedule data.

Production settings come from environment variables. `.env` is never committed. Enable secure cookies, HTTPS redirect, HSTS, trusted origins, and production host restrictions only in production settings.

Login failures use a short cache-backed per-IP-and-username cooldown with generic authentication errors. Do not log passwords, session cookies, concept content, or full search terms. A strict CSP is intentionally staged because the current server templates use an inline theme bootstrap and Alpine attributes; do not add `unsafe-eval` as a shortcut.

## Testing and checks

Use Django's built-in test runner initially. Test behavior that protects data or user boundaries: authentication, ownership, concept CRUD, category cycle prevention, relations, search, review submissions, and scheduling. Add one focused regression test for non-trivial bugs. Run `python manage.py check` and relevant tests before handoff; avoid coverage targets that reward meaningless tests.

For HTMX requests, `static/js/app.js` attaches the Django CSRF cookie as `X-CSRFToken` on `htmx:configRequest`. HTMX endpoints return a focused partial; full-page endpoints return their page template.

PWA caching may include only reviewed public shell assets and the offline page. Do not cache authenticated HTML, API responses, or private concept content without an explicit logout/privacy and conflict strategy. Bump the service-worker cache version whenever its precached asset list changes.

Offline private data is an explicit IndexedDB replica, never authenticated HTML in Cache Storage. Keep its DTOs owner-scoped and `Cache-Control: no-store`; do not store passwords, session cookies, or bearer tokens. Any supported local mutation needs a client UUID, idempotent server receipt, aggregate base version, and conflict result rather than a silent overwrite. Logout/clear-data paths must remove private IndexedDB stores; browser storage is not encrypted by MindRepo.

Search must stay entirely inside MindRepo infrastructure. Normalize conservatively: whitespace/case plus Arabic/Persian yeh and kaf variants, while preserving developer punctuation such as `C++`, `C#`, and `Node.js`. Do not log full private query strings at normal production log levels. Search pages, palette responses, favorites, and random recall remain private dynamic HTML and must not be added to the service-worker cache.

## Data and performance

Use `select_related` and `prefetch_related` for displayed relationships. Library listings select categories/prefetch tags; concept detail prefetches child records and relation targets. Add indexes after identifying the query path. Keep exports/imports in a future `knowledge` portability module or management command, with schema versioning and validation; do not add an API just for export.

Private Concept attachments use generated storage names and authenticated owner-checked `FileResponse` downloads. Do not expose `MEDIA_ROOT` through a web-server media alias. Validate extension, reported MIME type, and size server-side; attachment binaries stay out of IndexedDB and normal JSON export.

The Concept editor self-hosts Ace 1.36.2 and SortableJS 1.15.3 only on create/edit pages. Do not replace them with CDN references or move scheduling/domain validation into editor JavaScript.

## Review conventions

Scheduling calculations are pure and deterministic: pass an explicit timezone-aware timestamp and use the same function for rating previews and persisted ratings. Never place intervals in templates, JavaScript, or views. Submission belongs in the transactional review service; queue ordering belongs in review selectors. Keep logs immutable, use fixed clocks in scheduler tests, and do not cache private review pages or queue responses in the service worker.
