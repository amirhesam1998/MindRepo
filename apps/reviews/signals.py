import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.knowledge.models import Concept

from .models import ConceptReviewState


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Concept)
def create_review_state(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        ConceptReviewState.objects.get_or_create(concept=instance, defaults={"due_at": timezone.now()})
    except Exception:
        logger.exception("Could not create a review state for concept %s", instance.pk)
