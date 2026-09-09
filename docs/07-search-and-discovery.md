# Search and discovery

Analytics and data portability are separate private routes; neither changes search ranking or adds private dynamic pages to the service-worker cache.

## Scope

Level 5 makes private knowledge retrieval fast without an external search service. It provides `/search/`, a desktop Ctrl/Cmd+K command palette, favorites, and `/random/` Random Recall.

## Shared search contract

`apps.search.selectors.search_concepts(user, query, filters=None, limit=None)` is the only text-search path. Search, palette, and Library text filtering use it. The selector starts with the authenticated owner's concepts and never accepts an owner identifier from a request.

The query is capped at 200 characters. It collapses whitespace, case-folds, and treats Arabic/Persian yeh and kaf variants as equivalents. It deliberately preserves technical punctuation, so terms such as `C++`, `Node.js`, `HTTP/2`, and `N+1` remain meaningful.

## Ranking and fields

The portable score order is: exact title, title prefix, exact alias, partial alias, exact tag, partial tag, exact category, partial category, title partial, Quick Definition, Simple Explanation, then Deep Dive. Category matching covers concepts directly assigned to that category; recursive ancestor expansion is intentionally deferred.

Search covers concept title and the three textual depths, aliases, tags, and direct category title. It does not search code bodies, snippets, mistakes, or relations by default because those would add noise to the primary retrieval workflow.

## Database behavior

SQLite uses portable case-insensitive Django ORM matching with explicit weighted boosts. PostgreSQL additionally annotates `SearchVector`/`SearchQuery`/`SearchRank` over title and content depth as a tie-breaker. Portable owner/title indexes were added for concepts and categories. No `pg_trgm` extension, trigram indexes, or GIN indexes are installed in Level 5; production PostgreSQL full-text behavior was not runtime-tested in this workspace. Add typo-tolerant trigram search only after validating it against the production database.

## Interface behavior

The Search page supports category, tag, difficulty, favorite, and sort filters with 20-result pagination. The command palette returns at most eight results after a 200ms HTMX debounce. It uses a native dialog, keeps focus in the input, supports Arrow keys, Enter, Escape, and returns focus to the trigger. On mobile Ctrl/Cmd+K routes to the full Search page instead of forcing a desktop modal.

Favorites use the existing boolean field and an owner-scoped CSRF-protected POST toggle. Random Recall selects from the current user's scoped set, can be limited to favorites/category/difficulty, avoids the immediate previous concept when another choice exists, and uses GET-only reveal/navigation. It never creates a `ReviewLog` or updates `ReviewCardState`; “Review this concept” is an explicit link to the real review flow.

## Privacy and offline

Queries are not sent to third parties and recent searches are intentionally not persisted. Search, palette, favorites, and random pages are private dynamic HTML; the service worker still caches only named static assets and the public offline fallback. Offline search and private offline content remain Level 6 work.

Level 6 adds an opt-in IndexedDB local-search fallback with the same conservative title/alias/tag/category/content priority. It is deliberately simpler than online PostgreSQL ranking and does not cache the private Search page.

Advanced Concept search also considers section titles/content, source titles/notes, technology/version contexts, and ReviewCard question/answer, while still returning one deduplicated parent Concept. Title, aliases, tags, and category remain higher-priority signals. Random Recall remains Concept-level and never mutates card schedule state or ReviewLogs.
