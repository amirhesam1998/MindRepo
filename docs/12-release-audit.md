# Release audit — 2026-09-08

## Decision

**NO-GO.** SQLite validation is passing, but the production PostgreSQL path and the browser IndexedDB/Service Worker flow have not yet been run in this environment. Offline Knowledge is therefore disabled by default in production through `OFFLINE_KNOWLEDGE_ENABLED=False`.

## Scope and evidence

- Reviewed settings, routes, models, migrations, owner scoping, review scheduling, search, offline sync, PWA files, import/export, analytics, deployment examples, tests, and documentation.
- SQLite automated suite, Django checks, migration drift check, static collection, and JavaScript syntax checks are recorded in the release handoff after this audit.
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

## Required gates before GO

1. Run migrations and the test suite against a real PostgreSQL instance, including the PostgreSQL search branch.
2. Run a real browser test: enable offline data, bootstrap, disconnect, search/read/random recall, mutate a favorite, reconnect/sync, resolve a conflict, log out, and verify IndexedDB cleanup.
3. Perform and record an isolated PostgreSQL `pg_dump` to `pg_restore` recovery rehearsal.
4. Commit and tag the release candidate; this working tree currently has no usable commit evidence for release traceability.

## Non-blocking debt

- The internal scheduler is `mindrepo-v1`, not FSRS.
- Per-user timezone preference, trigram typo search, strict CSP, offline Concept editing, offline Review, and change-log retention remain intentionally deferred.
- The one-host file cache provides shared local Gunicorn-worker throttling, not multi-host global throttling.
