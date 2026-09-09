# Offline Knowledge and synchronization

Offline Knowledge is a per-browser opt-in at `/settings/offline/`. Private knowledge is structured IndexedDB data, never cached authenticated HTML or sync JSON. `OFFLINE_KNOWLEDGE_ENABLED` is enabled for development and remains disabled by default in production until the target-browser flow is verified.

## Protocol and local schema v2

`OFFLINE_SYNC_PROTOCOL_VERSION = 2`. Bootstrap and change requests must present protocol version 2; a v1 client receives `upgrade_required` with `full_resync_required: true`. Concept aggregate v2 includes normal Concept fields plus Markdown sections, sources, technology/version contexts, freshness, diagram source, and suitable attachment metadata. Scheduled review remains server-authoritative.

The IndexedDB database remains `mindrepo-private-v1`, upgraded through IndexedDB version 2. The migration preserves account metadata, conflicts, and compatible pending Favorite mutations, clears only the stale canonical Concept replica, then requires a v2 bootstrap. Pending work is never silently discarded.

Offline renderers use safe DOM text handling. Markdown may fall back to readable source; Mermaid may render from static assets or fall back to source. Neither can make offline Concept access fail. Private content is not moved into Cache Storage.

## Privacy and synchronization

IndexedDB is not encrypted by MindRepo: enable it only on a trusted device. Logout and Clear Offline Data remove account-partitioned replica data and queued mutations; static caches remain because they contain no private knowledge.

The server is canonical. Ordered owner-scoped changes carry upserts and delete tombstones. `Concept.sync_version` protects the full aggregate. Pending mutations use owner-scoped idempotency receipts; the supported browser write is Favorite toggle. Offline review, concept editing, and binary attachment access are intentionally unsupported.
