from django.conf import settings
from django.db import models


class OfflineChange(models.Model):
    class Operation(models.TextChoices):
        UPSERT = "upsert", "Upsert"
        DELETE = "delete", "Delete"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offline_changes")
    entity_id = models.PositiveIntegerField()
    operation = models.CharField(max_length=8, choices=Operation.choices)
    entity_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["owner", "id"])]


class AppliedClientMutation(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="offline_mutations")
    client_mutation_id = models.UUIDField()
    result = models.JSONField(default=dict)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "client_mutation_id"], name="offline_mutation_owner_id_unique")]
