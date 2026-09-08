from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.knowledge.models import Concept

from .models import OfflineChange


@receiver(post_save, sender=Concept)
def record_concept_upsert(sender, instance, **kwargs):
    OfflineChange.objects.create(
        owner=instance.owner,
        entity_id=instance.pk,
        operation=OfflineChange.Operation.UPSERT,
        entity_version=instance.sync_version,
    )


@receiver(pre_delete, sender=Concept)
def record_concept_delete(sender, instance, **kwargs):
    OfflineChange.objects.create(
        owner=instance.owner,
        entity_id=instance.pk,
        operation=OfflineChange.Operation.DELETE,
        entity_version=instance.sync_version + 1,
    )
