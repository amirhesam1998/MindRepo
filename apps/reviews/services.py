from django.db import transaction

from .models import ConceptReviewState, ReviewLog
from .scheduling import SCHEDULER_VERSION, schedule


class StaleReviewError(Exception):
    pass


def submit_review(*, user, state_id, rating, version, reviewed_at):
    with transaction.atomic():
        state = (
            ConceptReviewState.objects.select_for_update()
            .select_related("concept")
            .get(pk=state_id, concept__owner=user)
        )
        if state.version != version:
            raise StaleReviewError("This review card is no longer current.")
        result = schedule(state, rating, reviewed_at)
        ReviewLog.objects.create(
            concept=state.concept,
            rating=rating,
            reviewed_at=reviewed_at,
            previous_status=state.status,
            new_status=result.status,
            previous_due_at=state.due_at,
            new_due_at=result.due_at,
            previous_interval_days=state.interval_days,
            new_interval_days=result.interval_days,
            scheduler_version=SCHEDULER_VERSION,
        )
        state.status = result.status
        state.due_at = result.due_at
        state.last_reviewed_at = reviewed_at
        state.interval_days = result.interval_days
        state.review_count += 1
        state.lapse_count += result.lapse_delta
        state.success_streak = result.success_streak
        state.version += 1
        state.save()
        return state
