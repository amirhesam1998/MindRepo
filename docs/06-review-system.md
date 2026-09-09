# Review system

MindRepo schedules cards, not whole Concepts. Every Concept has one persistent `concept_recall` ReviewCard whose prompt and answer derive from the title and quick definition. Users may add independent basic cards with Markdown answers and optional hints.

## State and history

Each ReviewCard has exactly one `ReviewCardState`: `new`, `learning`, `review`, or `relearning`, with timezone-aware due time, interval, counts, scheduler metadata, and an optimistic version. Every accepted rating writes an immutable `ReviewLog` attached to that card and its parent Concept.

Migration `reviews.0003` created a default card for every existing Concept, copied the complete legacy `ConceptReviewState`, and attached historical logs to that card. `ConceptReviewState` remains a compatibility projection for the default card; it is not the primary scheduler state.

Custom cards can be archived. Archive and restore keep the card, `ReviewCardState`, and ReviewLogs unchanged. Archived cards are excluded from the queue and Concept mastery aggregation; restoring returns the card to its existing schedule.

## Scheduler, queue, and mastery

`mindrepo-v1` remains a pure deterministic scheduler. `reviews.services.submit_review()` locks and version-checks the card state, calculates the result, appends one log, and saves atomically. The queue is owner-scoped: overdue established cards, due established cards, then new cards, with ten new cards per configured application day.

Concept mastery aggregates active cards qualitatively: all new is New; any new/learning/relearning activity is Learning; established active cards are Familiar unless every active card satisfies Strong. Strong requires review state, at least three successful reviews, and a 21-day interval.

Random Recall remains Concept-level and never changes ReviewCardState or creates ReviewLogs. Scheduled review remains online-only; no client scheduler or offline rating queue exists.
