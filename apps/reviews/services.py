from django.db import transaction

from .models import ConceptReviewState, ReviewCardState, ReviewLog
from .scheduling import SCHEDULER_VERSION, schedule


class StaleReviewError(Exception):
    pass


def submit_review(*, user, state_id, rating, version, reviewed_at):
    with transaction.atomic():
        state = ReviewCardState.objects.select_for_update().select_related("card", "card__concept").filter(
            pk=state_id, card__concept__owner=user, card__is_active=True
        ).first()
        if not state:  # compatibility for callers holding a legacy state id
            legacy = ConceptReviewState.objects.filter(pk=state_id, concept__owner=user).first()
            if not legacy:
                raise ReviewCardState.DoesNotExist
            state = ReviewCardState.objects.select_for_update().select_related("card", "card__concept").get(
                card__concept=legacy.concept, card__card_type="concept_recall"
            )
        if state.version != version:
            raise StaleReviewError("This review card is no longer current.")
        result = schedule(state, rating, reviewed_at)
        ReviewLog.objects.create(
            concept=state.card.concept,
            card=state.card,
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
        if state.card.card_type == state.card.Type.CONCEPT_RECALL:
            # Keep the transitional Concept-level state truthful for legacy
            # detail, analytics, and API callers without firing its mirror signal.
            ConceptReviewState.objects.filter(concept=state.card.concept).update(
                status=state.status,
                due_at=state.due_at,
                last_reviewed_at=state.last_reviewed_at,
                review_count=state.review_count,
                lapse_count=state.lapse_count,
                success_streak=state.success_streak,
                interval_days=state.interval_days,
                version=state.version,
                scheduler_data=state.scheduler_data,
            )
        return state
