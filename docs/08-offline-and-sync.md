# Offline Knowledge and synchronization

## Privacy model

Offline Knowledge is an explicit per-browser opt-in at `/settings/offline/`. The service worker still caches only public/static shell files; it never stores private HTML, Search/Favorites/Review pages, Concept pages, or sync JSON. Private content is a structured IndexedDB replica named `mindrepo-private-v1`.

`OFFLINE_KNOWLEDGE_ENABLED` gates the settings page and every private sync endpoint. It is enabled by default in development and disabled by default in production pending a real-browser release check. This keeps PWA installation and the public fallback available without shipping unverified private browser storage.

IndexedDB is browser storage, not MindRepo encryption. Enable it only on a trusted device. Clear Offline Data and normal logout remove the private stores, pending mutations, and local opt-in flag. Static caches remain because they contain no private data. Browser storage can still be exposed by a compromised/shared device before it is cleared.

## Replica and reads

Schema v1 has `meta`, `concepts`, `pending_mutations`, and `conflicts` stores. `concepts` holds one denormalized Concept aggregate: base fields, category, tags, aliases, snippets, mistakes, and relation summaries. A stored account key partitions documents; a changed account clears the replica rather than mixing users.

Offline fallback can browse, locally rank/search, open a concept's safe text-only detail, inspect code/mistakes/relations, favorite/unfavorite, and run casual Random Recall. Local rendering uses DOM text APIs, never injected HTML. Offline Review, ReviewLog creation, and scheduler changes are unsupported.

## Protocol v1

`GET /offline/bootstrap/` returns a paged owner-scoped snapshot (100 concepts maximum) and snapshot cursor. `GET /offline/changes/?cursor=` returns ordered upsert/delete changes (100 maximum). Both are authenticated JSON with `Cache-Control: no-store`.

`POST /offline/mutations/` accepts at most 20 mutations. Current client UI supports the safe favorite toggle. The endpoint also validates create/update payloads for the protocol so future reduced offline capture can reuse it, but offline concept create/edit/delete UI is intentionally deferred. Each mutation has a UUID `client_mutation_id`; `(owner, client_mutation_id)` is unique and stores the canonical result, making retries idempotent.

The client pushes pending mutations, then pulls changes. Network failures keep pending work. Invalid mutations stop retrying and need attention; authentication failures retain work but ask the user to sign in again. Browser online state is a hint only; successful requests determine sync success.

## Versions, conflicts, and deletes

Concept is the aggregate root. `Concept.sync_version` increments on normal online and mutation-path saves. Nested aggregate content is included in the versioned document, so a concurrent nested edit conflicts at the whole-concept level rather than performing unsafe text merging.

An update with a stale `base_version` returns HTTP 409 and the current canonical document. The stale mutation is paused. The settings screen offers whole-document choices: **Keep Server Version** replaces the local document and removes that mutation; **Keep My Offline Version** removes the stale mutation and sends one explicit force update acknowledging the current server version. This is deliberate manual conflict resolution, not automatic text merge.

Create/update/delete/favorite lifecycle changes produce `OfflineChange` records. A deleted Concept becomes a tombstone in the feed, so clients remove it. A mutation targeting a server-deleted Concept never resurrects it automatically; it is marked for attention.

## Scope and limits

The server remains authoritative. IndexedDB is a replica plus a queue, not a second database. Sync metadata contains no cookies, passwords, or tokens. There is no background-sync correctness dependency, no aggressive polling, and no offline review submission. A future protocol version can add reduced offline concept capture/edit UI, nested editing, delete semantics, cursor retention/full-resync handling, and more polished browser-level sync testing.

Level 7 imports create normal server Concepts, so enabled devices receive them through the ordinary change feed. Exports only contain server-synced data; browser-only pending mutations remain outside export by design.
