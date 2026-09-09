# Advanced knowledge model

MindRepo keeps quick definition, simple explanation, deep dive, snippets, mistakes, relations, and attachments, then adds structured content for large technical topics.

## Sections and Markdown

`ConceptSection` is ordered and typed: standard, key takeaways, note, warning, best practices, comparison, or diagram. Simple explanation, deep dive, sections, and custom ReviewCard answers use Markdown source. The editor has a native toolbar and authenticated POST preview; both preview and detail call the same server renderer. Raw HTML is disabled, Markdown output is allowlist-sanitized, links are restricted to safe schemes, and remote Markdown images are not used.

Tables receive a responsive wrapper. Inline and fenced code remain safe text. Mermaid 11.4.1 is self-hosted, initialized with strict security and HTML labels disabled. Diagram source is never injected as HTML; invalid diagrams show a source fallback.

## Sources, context, and freshness

`ConceptSource` stores optional safe HTTP(S) reference metadata and is never fetched by MindRepo. `ConceptContext` stores technology, optional version, note, and order. Concept freshness is user-maintained (`current`, `needs_verification`, `outdated`) with verification date and note; **Mark verified today** is a POST action.

## Review cards

Each Concept has exactly one default `concept_recall` card. Custom basic cards have independent `ReviewCardState` schedules and logs. They are editable and sortable while active. Archived custom cards are shown in a dedicated collapsed editor group; restoring preserves state and history. The default card can never be archived.

The legacy ConceptReviewState migration created the default card, copied all scheduler fields, and assigned existing ReviewLogs to it. The old state is retained as a compatibility projection only. Random Recall remains Concept-level.

## Revision history

Successful content saves create immutable `ConceptRevision` snapshots. History provides owner-scoped list, view, compare, and POST restore. Restore updates content, sections, sources, contexts, and card wording/order/status, then produces a new restore revision and sync-visible Concept update. It never rewinds ReviewCardState, ReviewLogs, or attachment binaries. Missing historical cards are recreated inactive; the default card remains unique.

## Portability and offline

JSON export format v2 includes sections, sources, contexts, freshness, and ReviewCard content; v1 imports remain supported. Markdown ZIP exports readable content, Mermaid fences, and owned attachment binaries. JSON stores attachment metadata only. Revision snapshots are database data but are not part of the normal portability export.

Offline protocol v2 transports the safe reading aggregate and requires a full v2 bootstrap after local schema migration. Offline scheduled review, Concept editing, and attachment binaries remain unsupported. See docs 06, 08, and 09 for their respective contracts.
