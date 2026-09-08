# Roadmap

## Level 7 — complete

Analytics, portable JSON/Markdown export, validated import preview, production deployment examples, backups, health checks, login throttling, and CI are implemented. Advanced operational monitoring, per-user timezones, and high-scale import processing remain future work.

## Level 0 — complete

Repository inspection, architecture, domain decisions, conventions, environment template, dependency declaration, and delivery roadmap.

## Level 1 — Django foundation

Create the Django project, settings split, custom user, authentication, root URLs, base layout, static assets, and basic checks. No knowledge CRUD yet.

### Completion

Implemented in Level 1: split settings, custom user, login/logout, protected dashboard, admin registration, responsive app shell, theme foundation, and authentication tests. Knowledge CRUD remains deferred.

## Level 2 — knowledge system

Implement category hierarchy, concepts, aliases, tags, relations, snippets, and owner-safe CRUD with migrations and focused tests.

### Completion

Implemented: the `knowledge` app; private adjacency-list categories; nullable-category concepts; tags, aliases, ordered snippets, structured mistakes, and directed typed relations; Library filtering/sorting/pagination; dashboard metrics; and ownership/XSS-focused tests. Spaced repetition and advanced search remain deferred.

## Level 3 — responsive UI and PWA foundation

Refine responsive reading UI and add the manifest, installability, and basic static service-worker caching. Dashboard, library navigation, dedicated mobile navigation, and dark-mode tokens were established earlier.

### Completion

Implemented: responsive product UI polish, progressive concept capture, reading-focused concept detail, mobile navigation/safe-area behavior, theme refinements, manifest/icons, static-only service-worker cache, online/offline indication, and a public offline fallback. Private offline knowledge remains deliberately deferred.

## Level 4 — spaced repetition

Implement review queue, reveal-and-rate session, immutable review records, schedule state, and the first replaceable scheduling algorithm.

### Completion

Implemented: the `reviews` app; one schedule state per concept; old-concept backfill; deterministic `mindrepo-v1` scheduling; atomic, version-checked review submissions; immutable review logs; due/new queue ordering with a daily new-card limit; history; qualitative mastery; dashboard and concept-detail review summaries; and focused review/security tests. Offline review, per-user time zones, reminders, and FSRS remain deferred.

## Level 5 — retrieval enhancements

Add command-palette search, PostgreSQL search improvements where applicable, favorites, random concept, and related-concept views.

### Completion

Implemented: a shared private ranked search selector; dedicated Search and mobile Search; Ctrl/Cmd+K palette; portable SQLite matching plus PostgreSQL full-text tie-breaking; favorites; and Random Recall that is explicitly independent from the review schedule. Offline search, trigram typo matching, and recent-search persistence remain deferred.

## Level 6 — complete: offline reading

Add IndexedDB-backed offline reading and an explicit synchronization/conflict design only after online flows are stable.

## Level 7 — complete: hardening and portability

Add import/export, backups, analytics where useful, security review, performance work, production settings, and deployment preparation.

## Level 6 completion

Implemented: opt-in per-device Offline Knowledge, a structured IndexedDB Concept replica, paged bootstrap and incremental change endpoints, deletion tombstones, concept aggregate versions, idempotent favorite mutation queue, manual whole-document conflict choices, offline Library/search/detail reading, and offline Random Recall. Private HTML remains uncached. Offline Concept create/edit/delete, complex nested mutation editing, and offline Review remain deferred.

## Concept editor refinement

Implemented after Level 7: fast capture, collapsible editor sections, token tags, self-hosted Ace editing, sortable snippets and mistakes, compact aliases/relations, and private concept attachments. Attachment binary offline sync remains deferred.
