# Review system

Versioned JSON portability includes canonical ReviewState and immutable ReviewLog records. Import validates ratings and timezone-aware log timestamps, then restores them only for newly imported Concepts; existing duplicate Concepts are never overwritten.

## Scope

Level 4 adds focused online review. It stores per-concept scheduling state and an immutable rating history; it does not add offline review, reminders, user preferences, or a scientific retention estimate.

## Data and lifecycle

Each `Concept` has exactly one `ConceptReviewState`. New concepts receive one through a post-save signal; migration `reviews.0001_initial` backfills existing concepts. The lifecycle is intentionally small:

| State | Meaning |
| --- | --- |
| `new` | Never rated. |
| `learning` | Being introduced with short steps. |
| `review` | Established with day-based intervals. |
| `relearning` | A lapsed established concept on a short recovery step. |

Every accepted rating appends a `ReviewLog` containing the previous and resulting lifecycle, due time, interval, rating, and scheduler version. Normal user flows cannot edit history. Deleting a concept cascades its associated review state and logs.

## Scheduler

`mindrepo-v1` is a small deterministic internal scheduler. `schedule(state, rating, reviewed_at)` is pure and returns a result without saving. The submission service uses that same function for previews and persistence, so displayed intervals match the eventual result.

| Current state | Again | Hard | Good | Easy |
| --- | --- | --- | --- | --- |
| New | learning, 10 minutes | learning, 1 day | review, 3 days | review, 7 days |
| Learning | learning, 20 minutes | learning, 1 day | review, 3 days | review, 7 days |
| Relearning | relearning, 30 minutes | relearning, 1 day | review, 3 days | review, 7 days |
| Review | relearning, 30 minutes | review, 1.2x interval | review, 2x interval | review, 2.8x interval |

Intervals have a 10-minute minimum and a 3,650-day maximum. `Again` on an established review increments the lapse count. The implementation stores neutral current-state fields plus contained `scheduler_data`, so a future SM-2 or FSRS adapter can replace `mindrepo-v1` without changing routes, templates, or history.

## Queue and session

The queue is scoped to the authenticated user and ordered as: overdue established cards, due established cards, then new cards. New introductions are capped at 10 per configured application day, while due cards always take priority. The session itself is intentionally not persisted: submitted ratings are durable, and refreshing or leaving rebuilds the remaining queue from current server state.

The card shows the concept title and prompt first. The answer must be revealed before ratings appear. `1`–`4` rate Again, Hard, Good, and Easy after reveal; Space or Enter reveals the answer. A rendered state version is verified during submission, and the state row is locked in a transaction to reject stale tabs and double submissions safely.

## Mastery and time

Mastery is qualitative rather than a claimed probability: `New`, `Learning`, `Familiar`, and `Strong`. Strong requires review status, at least three successful reviews, and an interval of at least 21 days. All due logic uses timezone-aware Django datetimes. There is not yet a per-user timezone preference, so daily limits and today statistics use the configured application timezone consistently.

## Privacy and offline behavior

Review pages, answer content, history, and schedule data are private. The service worker continues to cache only named static assets and the public offline fallback; it does not persist authenticated HTML or queue responses. If a rating is attempted offline, the browser shows that it was not saved. Offline reading, offline review submission, IndexedDB, and synchronization are Level 6 work.
