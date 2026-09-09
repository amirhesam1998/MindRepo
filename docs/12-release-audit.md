# Release audit — 2026-09-08

## Decision

**NO-GO.** SQLite validation is passing, but the production PostgreSQL path and the browser IndexedDB/Service Worker flow have not yet been run in this environment. Offline Knowledge is therefore disabled by default in production through `OFFLINE_KNOWLEDGE_ENABLED=False`.

## Scope and evidence

- Reviewed settings, routes, models, migrations, owner scoping, review scheduling, search, offline sync, PWA files, import/export, analytics, deployment examples, tests, and documentation.
- SQLite automated suite: **69 tests passed**. `manage.py check`, `makemigrations --check`, `migrate`, `ruff check .`, `uv lock --check`, `uv pip check`, `collectstatic --noinput`, and JavaScript checks for `static/js/app.js` and `static/js/offline.js` passed. A fresh temporary SQLite database migrated from zero and accepted a superuser.
- Production settings loaded with temporary audit values and `manage.py check --deploy` passed. Development test-client smoke checks returned 200 for `/health/`, `/manifest.webmanifest`, `/service-worker.js`, and `/offline/`, and 302 for anonymous private routes.
- PostgreSQL CI is configured but its execution result is not available in this workspace; configuration alone is not evidence.
- Browser automation is unavailable in this workspace, so IndexedDB, Service Worker registration, and the end-to-end offline flow remain unverified at runtime.

## Audit fixes

- Anchored paged offline bootstrap snapshots to prevent changes made during bootstrap from being skipped by the subsequent change feed.
- Made nested Concept form changes emit a final aggregate sync version/change so offline replicas receive aliases, snippets, mistakes, and relations updates.
- Paused stale offline mutations on conflict and remove the old mutation when a user keeps the server or explicitly keeps the local version.
- Gated every private Offline Knowledge endpoint as well as its settings UI behind `OFFLINE_KNOWLEDGE_ENABLED`.
- Aligned analytics mastery aggregation with the review-domain mastery definition.
- Hardened import validation for duplicate export identifiers, malformed nested collections, relations, and unsupported duplicate strategies.
- Corrected stale PWA cache-version and roadmap/readme status documentation; added cache/export/log ignore rules and `X-Real-IP` to the Nginx example.
- Corrected login throttling behind the trusted Nginx proxy: `X-Real-IP` is now accepted only from `TRUSTED_PROXY_IPS`, avoiding a proxy-wide throttle bucket while rejecting client-forged forwarding headers.

## Required gates before GO

1. Run migrations and the test suite against a real PostgreSQL instance, including the PostgreSQL search branch.
2. Run a real browser test: enable offline data, bootstrap, disconnect, search/read/random recall, mutate a favorite, reconnect/sync, resolve a conflict, log out, and verify IndexedDB cleanup.
3. Perform and record an isolated PostgreSQL `pg_dump` to `pg_restore` recovery rehearsal.
4. Commit the audit changes and tag the release candidate. The current repository has commit `8a7bbb1` (`init`), but this audit is not a release tag.

## Non-blocking debt

- The internal scheduler is `mindrepo-v1`, not FSRS.
- Per-user timezone preference, trigram typo search, strict CSP, offline Concept editing, offline Review, and change-log retention remain intentionally deferred.
- The one-host file cache provides shared local Gunicorn-worker throttling, not multi-host global throttling.

## Post-audit editor refinement

The Concept editor now adds private attachments and self-hosted Ace/Sortable assets. This introduces `knowledge.0004_conceptattachment`, requires `MEDIA_ROOT` to be included in operational backups, and leaves attachment binaries unavailable offline. The prior NO-GO decision remains unchanged until the PostgreSQL, browser Offline Knowledge, and restore gates are re-run.

## Advanced knowledge completion

The advanced knowledge implementation is code-complete: safe Markdown/preview, strict self-hosted Mermaid, revisions with content-only restore, card-level review including archived custom cards, export v2/v1 import, and offline protocol/IndexedDB v2. This does not clear the existing **NO-GO** gates: a real PostgreSQL run, real-browser offline validation, and isolated PostgreSQL backup-to-restore rehearsal remain unrecorded.
