from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.knowledge.models import Category, Concept
from apps.reviews.models import ConceptReviewState, ReviewLog
from apps.reviews.selectors import mastery_distribution


WINDOWS = {"7": 7, "30": 30, "90": 90}


def analytics_for_user(user, window="30"):
    """Return bounded, database-aggregated personal learning metrics."""
    days = WINDOWS.get(str(window), 30)
    now = timezone.now()
    start = now - timedelta(days=days - 1)
    concepts = Concept.objects.filter(owner=user)
    logs = ReviewLog.objects.filter(concept__owner=user, reviewed_at__gte=start)
    states = ConceptReviewState.objects.filter(concept__owner=user)
    ratings = {choice: logs.filter(rating=choice).count() for choice in ReviewLog.Rating.values}
    status_counts = {choice: states.filter(status=choice).count() for choice in ConceptReviewState.Status.values}
    mastery = mastery_distribution(user)
    activity = list(logs.annotate(day=TruncDate("reviewed_at")).values("day").annotate(count=Count("id")).order_by("day"))
    growth = list(concepts.filter(created_at__gte=start).annotate(day=TruncDate("created_at")).values("day").annotate(count=Count("id")).order_by("day"))
    return {"window": str(days), "concept_count": concepts.count(), "category_count": Category.objects.filter(owner=user).count(), "favorite_count": concepts.filter(is_favorite=True).count(), "created_window": concepts.filter(created_at__gte=start).count(), "reviews": {"today": logs.filter(reviewed_at__gte=timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)).count(), "window": logs.count(), "ratings": ratings}, "states": status_counts, "mastery": mastery, "activity": activity, "growth": growth}
