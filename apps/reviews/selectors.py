from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import ConceptReviewState, ReviewLog
from .scheduling import NEW_CARDS_PER_DAY


def review_states_for_user(user):
    return ConceptReviewState.objects.filter(concept__owner=user).select_related("concept", "concept__category").prefetch_related("concept__tags")


def introduced_today(user, now):
    start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    return ReviewLog.objects.filter(
        concept__owner=user,
        previous_status=ConceptReviewState.Status.NEW,
        reviewed_at__gte=start,
        reviewed_at__lt=start + timedelta(days=1),
    ).count()


def build_review_queue(user, now, *, manual_concept_id=None, new_limit=NEW_CARDS_PER_DAY):
    states = review_states_for_user(user)
    queue = []
    queued_ids = set()
    if manual_concept_id:
        manual = states.filter(concept_id=manual_concept_id).first()
        if manual:
            queue.append(manual)
            queued_ids.add(manual.pk)
    due = states.filter(~Q(status=ConceptReviewState.Status.NEW), due_at__lte=now).order_by("due_at", "pk")
    for state in due:
        if state.pk not in queued_ids:
            queue.append(state)
            queued_ids.add(state.pk)
    remaining_new = max(0, new_limit - introduced_today(user, now))
    new = states.filter(status=ConceptReviewState.Status.NEW, due_at__lte=now).order_by("due_at", "concept__created_at", "pk")[:remaining_new]
    for state in new:
        if state.pk not in queued_ids:
            queue.append(state)
            queued_ids.add(state.pk)
    return queue


def due_count(user, now):
    return review_states_for_user(user).filter(~Q(status=ConceptReviewState.Status.NEW), due_at__lte=now).count()


def new_count(user, now):
    return review_states_for_user(user).filter(status=ConceptReviewState.Status.NEW, due_at__lte=now).count()


def reviewed_today_count(user, now):
    start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    return ReviewLog.objects.filter(concept__owner=user, reviewed_at__gte=start, reviewed_at__lt=start + timedelta(days=1)).count()


def next_due(user, now):
    return review_states_for_user(user).filter(due_at__gt=now).order_by("due_at").values_list("due_at", flat=True).first()


def mastery_level(state):
    if state.status == ConceptReviewState.Status.NEW:
        return "New"
    if state.status in {ConceptReviewState.Status.LEARNING, ConceptReviewState.Status.RELEARNING}:
        return "Learning"
    if state.interval_days >= 21 and state.success_streak >= 3:
        return "Strong"
    return "Familiar"


def mastery_distribution(user):
    """Database aggregate matching ``mastery_level`` without materializing states."""
    states = ConceptReviewState.objects.filter(concept__owner=user)
    new = states.filter(status=ConceptReviewState.Status.NEW).count()
    learning = states.filter(status__in=[ConceptReviewState.Status.LEARNING, ConceptReviewState.Status.RELEARNING]).count()
    strong = states.filter(status=ConceptReviewState.Status.REVIEW, interval_days__gte=21, success_streak__gte=3).count()
    return {"new": new, "learning": learning, "strong": strong, "familiar": max(0, states.count() - new - learning - strong)}
