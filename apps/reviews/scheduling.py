from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from .models import ConceptReviewState, ReviewLog


SCHEDULER_VERSION = "mindrepo-v1"
MAX_INTERVAL_DAYS = 3650
NEW_CARDS_PER_DAY = 10


@dataclass(frozen=True)
class SchedulingResult:
    status: str
    due_at: object
    interval_days: int
    lapse_delta: int
    success_streak: int


def _result(status, reviewed_at, interval_days, *, minutes=0, lapse_delta=0, success_streak=0):
    interval_days = max(0, min(interval_days, MAX_INTERVAL_DAYS))
    delay = timedelta(minutes=minutes) if minutes else timedelta(days=max(1, interval_days))
    return SchedulingResult(status, reviewed_at + delay, interval_days, lapse_delta, success_streak)


def schedule(state, rating, reviewed_at):
    """Pure deterministic scheduler for the initial MindRepo learning flow."""
    if timezone.is_naive(reviewed_at):
        raise ValueError("reviewed_at must be timezone-aware")
    if rating not in ReviewLog.Rating.values:
        raise ValueError("Unknown review rating")

    status = state.status
    streak = state.success_streak
    if status == ConceptReviewState.Status.NEW:
        outcomes = {
            ReviewLog.Rating.AGAIN: _result(ConceptReviewState.Status.LEARNING, reviewed_at, 0, minutes=10),
            ReviewLog.Rating.HARD: _result(ConceptReviewState.Status.LEARNING, reviewed_at, 1),
            ReviewLog.Rating.GOOD: _result(ConceptReviewState.Status.REVIEW, reviewed_at, 3, success_streak=1),
            ReviewLog.Rating.EASY: _result(ConceptReviewState.Status.REVIEW, reviewed_at, 7, success_streak=1),
        }
        return outcomes[rating]

    if status in {ConceptReviewState.Status.LEARNING, ConceptReviewState.Status.RELEARNING}:
        relearning = status == ConceptReviewState.Status.RELEARNING
        outcomes = {
            ReviewLog.Rating.AGAIN: _result(status, reviewed_at, 0, minutes=20 if not relearning else 30),
            ReviewLog.Rating.HARD: _result(status, reviewed_at, 1),
            ReviewLog.Rating.GOOD: _result(ConceptReviewState.Status.REVIEW, reviewed_at, 3, success_streak=streak + 1),
            ReviewLog.Rating.EASY: _result(ConceptReviewState.Status.REVIEW, reviewed_at, 7, success_streak=streak + 1),
        }
        return outcomes[rating]

    interval = max(1, state.interval_days)
    outcomes = {
        ReviewLog.Rating.AGAIN: _result(ConceptReviewState.Status.RELEARNING, reviewed_at, 0, minutes=30, lapse_delta=1),
        ReviewLog.Rating.HARD: _result(ConceptReviewState.Status.REVIEW, reviewed_at, round(interval * 1.2), success_streak=streak + 1),
        ReviewLog.Rating.GOOD: _result(ConceptReviewState.Status.REVIEW, reviewed_at, round(interval * 2), success_streak=streak + 1),
        ReviewLog.Rating.EASY: _result(ConceptReviewState.Status.REVIEW, reviewed_at, round(interval * 2.8), success_streak=streak + 1),
    }
    return outcomes[rating]


def interval_label(result, reviewed_at):
    seconds = max(0, int((result.due_at - reviewed_at).total_seconds()))
    if seconds < 3600:
        return f"{max(1, seconds // 60)} min"
    if seconds < 86400:
        return f"{max(1, seconds // 3600)} hr"
    return f"{max(1, seconds // 86400)} day" + ("s" if seconds // 86400 != 1 else "")
