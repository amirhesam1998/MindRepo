# Architecture

## Shape

MindRepo will be a Django modular monolith with server-rendered templates. Django owns routing, authentication, authorization, forms, HTML rendering, and database access. HTMX enhances focused interactions; Alpine.js is limited to small client-side state such as dialogs, navigation, and theme controls.

The planned app boundaries are:

| App | Responsibility |
| --- | --- |
| `core` | shared layout, dashboard/home, shared template utilities, static PWA endpoints |
| `accounts` | custom user model and Django authentication integration |
| `knowledge` | categories, concepts, aliases, tags, snippets, and concept relations |
| `reviews` | review history, per-concept schedule state, queue, and scheduling orchestration |
| `search` | cross-knowledge search queries and command-palette endpoints |
| `offline` | opt-in sync protocol, owner-scoped changes, mutation receipts, and IndexedDB-facing DTOs |

`reviews`, `search`, and `offline` are introduced only when their Level 4–6 responsibilities are needed. `offline` does not own knowledge or review scheduling; it serializes the Concept aggregate and applies the small explicitly supported mutation set.

`pwa` is not a separate Django app: `core` serves the manifest, root-scoped service worker, and public offline fallback; icons remain static assets. Create a separate app only if PWA behavior grows beyond those boundaries.

## Settings and dependencies

Use Python 3.12+, Django 5.2 LTS, and `pyproject.toml` as the dependency source of truth. Level 1 adds `config/settings/base.py`, `development.py`, and `production.py`; environment variables select secrets and deployment behavior. SQLite is the development default. Production uses PostgreSQL.

Level 1 uses `python-dotenv` to load a local `.env` and `psycopg` for PostgreSQL connections. A compact standard-library URL parser supports SQLite and PostgreSQL instead of adding a general database-URL package. `uv.lock` records resolved dependencies.

Avoid new dependencies unless Django, Python, Bootstrap, HTMX, Alpine, or a browser feature cannot meet the concrete requirement. The first external additions likely needed later are a PostgreSQL URL parser and a production server, only when their level requires them.

## Request and business-logic boundaries

Views authenticate, load only user-owned records, validate forms, and choose a template or HTMX partial. Level 2 uses Django inline formsets inside one `transaction.atomic()` block for concept child records. Templates render data and contain no business decisions. Models express data integrity and small local behavior. Multi-record or algorithmic work belongs in a small app-local service module, for example `reviews/services/scheduling.py`.

Do not create generic repositories, service interfaces, or domain frameworks. Straightforward CRUD stays in Django forms, views, and models.

## Data access and search

Use the Django ORM and select/prefetch related data for list and detail views. The `search` app owns the reusable `search_concepts()` selector used by Search, the command palette, and Library text filtering. It always begins from `Concept.objects.filter(owner=user)` and returns a ranked queryset with only the category, review state, tags, and aliases required for discovery cards.

SQLite uses portable case-insensitive, weighted matching. PostgreSQL adds Django `SearchVector`/`SearchQuery`/`SearchRank` as a tie-breaker after explicit title, alias, tag, and category boosts. There is no external search service, extension, or PostgreSQL-only migration at this stage; trigram typo tolerance can be added later only after a measured need and production PostgreSQL verification.

## Review architecture

`reviews` owns `ConceptReviewState` and immutable `ReviewLog` records; `knowledge` remains the owner of stored concepts. A post-save signal creates a state for each new concept, the initial migration backfills pre-existing concepts, and concept detail has a safe lazy fallback for an interrupted creation path.

`reviews.scheduling.schedule(state, rating, reviewed_at)` is a pure, versioned `mindrepo-v1` calculation. `reviews.services.submit_review()` locks the state, verifies its optimistic version, calculates the schedule, writes a log, and saves the next state inside one transaction. Queue selectors build a user-scoped queue without loading the library into memory. This isolates a future SM-2 or FSRS adapter from views, templates, and history.

## Discovery architecture

Favorites remain the existing `Concept.is_favorite` field; a small owner-scoped POST toggle replaces only the favorite control through HTMX. Random Recall is a `search`-app GET flow with a random offset over a scoped concept queryset. It is intentionally independent from `reviews`: it never updates state or creates `ReviewLog` records. A native dialog plus HTMX palette partial delivers Ctrl/Cmd+K on desktop; mobile uses the full Search page.

## Frontend architecture

Templates use a base layout, page templates, and reusable includes. Full-page requests return pages; HTMX requests return the smallest relevant partial. Bootstrap provides accessible foundations, while custom CSS defines semantic tokens and MindRepo-specific components. Tokens use CSS variables for light, dark, and system-selected themes; templates must not scatter raw color values.

Use CSS logical properties and direction-aware layout for RTL. Content is direction-aware, while code blocks always use `dir="ltr"`, left alignment, and a monospace stack. Mobile gets a dedicated bottom navigation; desktop gets a sidebar rather than a shrunken version of it.

## PWA and offline direction

The versioned worker caches only named static shell assets and `/offline/`; navigations are network-first and private authenticated HTML (including review queue, history, answers, concepts, search, and JSON) is never persistently cached. Level 6 adds a separate opt-in IndexedDB replica, never Cache Storage private content. The `offline` app supplies a paged bootstrap endpoint, ordered owner-scoped change feed, and idempotent mutation endpoint. Concept is the sync aggregate root: tags, aliases, snippets, mistakes, and relations are included in its document, and `sync_version` protects aggregate updates. Review remains server-only. See `docs/08-offline-and-sync.md`.

## Deployment direction

Deploy one Django application behind Gunicorn and Nginx on Linux with PostgreSQL and HTTPS. Run migrations as an explicit release step, serve collected static assets through Nginx, set secure Django cookie/HTTPS settings, and back up PostgreSQL. Docker is optional and deferred.

## Production additions

`core.analytics` aggregates user-owned Concept, ReviewState, and ReviewLog data in the database. `knowledge.portability` owns versioned JSON/Markdown export and validated import planning/application; it is intentionally not a general API. `/health/` is a public liveness response without diagnostics. See docs 09–11 for operational detail.
