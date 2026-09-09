import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.knowledge.models import Concept

from .models import ConceptReviewState, ReviewCard, ReviewCardState


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Concept)
def create_review_state(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        ConceptReviewState.objects.get_or_create(concept=instance, defaults={"due_at": timezone.now()})
        card, _ = ReviewCard.objects.get_or_create(
            concept=instance,
            card_type=ReviewCard.Type.CONCEPT_RECALL,
            defaults={"sort_order": 0},
        )
        ReviewCardState.objects.get_or_create(card=card, defaults={"due_at": timezone.now()})
    except Exception:
        logger.exception("Could not create a review state for concept %s", instance.pk)


@receiver(post_save, sender=ConceptReviewState)
def mirror_legacy_state_to_default_card(sender, instance, **kwargs):
    """Compatibility bridge while legacy ConceptReviewState remains available."""
    card, _ = ReviewCard.objects.get_or_create(concept=instance.concept, card_type=ReviewCard.Type.CONCEPT_RECALL)
    ReviewCardState.objects.update_or_create(
        card=card,
        defaults={
            "status": instance.status, "due_at": instance.due_at, "last_reviewed_at": instance.last_reviewed_at,
            "review_count": instance.review_count, "lapse_count": instance.lapse_count,
            "success_streak": instance.success_streak, "interval_days": instance.interval_days,
            "version": instance.version, "scheduler_data": instance.scheduler_data,
        },
    )


@receiver(post_save, sender=ReviewCard)
def create_review_card_state(sender, instance, created, **kwargs):
    if created:
        ReviewCardState.objects.get_or_create(card=instance, defaults={"due_at": timezone.now()})
