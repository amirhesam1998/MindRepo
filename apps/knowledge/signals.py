from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import ConceptAttachment


@receiver(post_delete, sender=ConceptAttachment)
def delete_private_attachment_file(sender, instance, **kwargs):
    """Delete only after the database deletion commits successfully."""
    storage, name = instance.file.storage, instance.file.name
    if name:
        transaction.on_commit(lambda: storage.delete(name))
