# PWA foundation

MindRepo serves `/manifest.webmanifest`, `/service-worker.js`, and `/offline/` from `core`. The service worker is root-scoped through `Service-Worker-Allowed: /`.

## Cache policy

`mindrepo-static-v3` precaches only the named local CSS, JavaScript, vendor files, icon assets, and the public offline page. It uses cache-first matching only for those exact static paths. Navigation requests use the network and fall back to `/offline/` only when unavailable. Private analytics, data settings, exports, imports, and JSON are never cached.

Private authenticated HTML, concept pages, API responses, and user data are not cached persistently. This is intentional: shared devices must not expose a prior user's knowledge after logout.

## Updates and deployment

When the precache list changes, bump the worker cache version and its activation cleanup removes older `mindrepo-static-*` caches. Production enables `PWA_ENABLED` by default and must use HTTPS. Local development keeps registration disabled by default; set `PWA_ENABLED=True` when testing on localhost.

## Offline Knowledge release gate

The current worker cache is `mindrepo-static-v3` and still contains only public/static shell files plus `/offline/`. Offline Knowledge is an opt-in IndexedDB replica, not a Cache Storage policy change. `OFFLINE_KNOWLEDGE_ENABLED` controls the private IndexedDB UI and sync endpoints; it is enabled for development and disabled by default in production until target-browser verification has completed. See `docs/08-offline-and-sync.md` for the security and synchronization rules.

Offline reading, IndexedDB, synchronization, and conflict handling are Level 6 work. iOS can install the app through Safari’s Add to Home Screen flow; browser install prompts vary by platform.
