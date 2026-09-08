from django.db import models
from django.utils import timezone

from apps.knowledge.models import Concept


class ConceptReviewState(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        LEARNING = "learning", "Learning"
        REVIEW = "review", "Review"
        RELEARNING = "relearning", "Relearning"

    concept = models.OneToOneField(Concept, on_delete=models.CASCADE, related_name="review_state")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    due_at = models.DateTimeField(default=timezone.now)
    last_reviewed_at = models.DateTimeField(blank=True, null=True)
    review_count = models.PositiveIntegerField(default=0)
    lapse_count = models.PositiveIntegerField(default=0)
    success_streak = models.PositiveIntegerField(default=0)
    interval_days = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=0)
    scheduler_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["status", "due_at"])]

    def __str__(self):
        return f"{self.concept} ({self.status})"


class ReviewLog(models.Model):
    class Rating(models.TextChoices):
        AGAIN = "again", "Again"
        HARD = "hard", "Hard"
        GOOD = "good", "Good"
        EASY = "easy", "Easy"

    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="review_logs")
    rating = models.CharField(max_length=8, choices=Rating.choices)
    reviewed_at = models.DateTimeField()
    previous_status = models.CharField(max_length=16, choices=ConceptReviewState.Status.choices)
    new_status = models.CharField(max_length=16, choices=ConceptReviewState.Status.choices)
    previous_due_at = models.DateTimeField()
    new_due_at = models.DateTimeField()
    previous_interval_days = models.PositiveIntegerField()
    new_interval_days = models.PositiveIntegerField()
    scheduler_version = models.CharField(max_length=32, default="mindrepo-v1")

    class Meta:
        ordering = ["-reviewed_at", "-pk"]
        indexes = [models.Index(fields=["concept", "-reviewed_at"]), models.Index(fields=["rating", "-reviewed_at"])]

    def __str__(self):
        return f"{self.concept} — {self.rating}"
