# Backup and recovery

Use three distinct protections:

- JSON export: user-readable, portable knowledge copy.
- PostgreSQL backup plus private `MEDIA_ROOT` attachment files: operational disaster recovery, using `pg_dump`/`pg_restore` and an off-host file copy.
- IndexedDB: convenience replica only; never a backup.

Recommended PostgreSQL retention is 7 daily, 4 weekly, and 6 monthly backups, with one off-server copy. Create a portable backup with `pg_dump --format=custom --file=mindrepo-YYYY-MM-DD.dump "$DATABASE_URL"`. Restore only into an isolated empty database with `createdb mindrepo_restore` followed by `pg_restore --clean --if-exists --dbname=mindrepo_restore mindrepo-YYYY-MM-DD.dump`; then point a temporary Django environment at that database, run `manage.py migrate` and `manage.py check`, verify representative concept/review counts, and verify a login. Never use the restore test to overwrite production.

Before an upgrade: make and verify a database backup and private attachment-storage copy, deploy code, install dependencies, migrate, collect static assets, restart, and check `/health/`. Restore the database first, then restore `MEDIA_ROOT` to its configured path before verifying attachment downloads. Roll back code only after considering whether its migrations are reversible. IndexedDB is not a backup, and a user JSON export is portable knowledge data rather than a full operational PostgreSQL recovery image.

Sections, Mermaid source, sources, contexts, freshness, ReviewCards, ReviewCardState, ReviewLogs, and ConceptRevision snapshots are PostgreSQL data. Full recovery still requires the matching private attachment directory; revision history cannot recover an attachment binary that the file backup lost.
