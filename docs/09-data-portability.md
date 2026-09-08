# Data portability

MindRepo exports only the current authenticated user's knowledge. JSON export is versioned (`mindrepo`, version 1), includes Categories, Concept aggregates, relations, favorites, review state, and immutable review logs, but never passwords, sessions, cookies, sync receipts, or server secrets. Markdown export is a ZIP of readable files with language-labelled code fences.

`/settings/data/` validates an uploaded MindRepo JSON export before any write. Preview is dry-run only. Import uses owner-local identifiers to rebuild category and concept relationships in one transaction. Duplicate titles can be skipped or imported as clearly named copies; imports always belong to the signed-in user and are normal sync-visible Concept changes.

The current upload ceiling is 2 MiB / 2,000 Concepts. JSON export is portable data, not a complete operational database backup. Unsynced browser-only changes are not included.
