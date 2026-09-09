from uuid import uuid4

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


class ReviewCard(models.Model):
    class Type(models.TextChoices):
        CONCEPT_RECALL = "concept_recall", "Concept recall"
        BASIC = "basic", "Basic"

    public_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="review_cards")
    card_type = models.CharField(max_length=20, choices=Type.choices, default=Type.BASIC)
    question = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "card_type"],
                condition=models.Q(card_type="concept_recall"),
                name="reviews_one_default_card_per_concept",
            )
        ]

    @property
    def display_question(self):
        return self.question or f"What is {self.concept.title}?"

    @property
    def display_answer(self):
        return self.answer or self.concept.quick_definition


class ReviewCardState(models.Model):
    card = models.OneToOneField(ReviewCard, on_delete=models.CASCADE, related_name="state")
    status = models.CharField(max_length=16, choices=ConceptReviewState.Status.choices, default=ConceptReviewState.Status.NEW)
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


class ReviewLog(models.Model):
    class Rating(models.TextChoices):
        AGAIN = "again", "Again"
        HARD = "hard", "Hard"
        GOOD = "good", "Good"
        EASY = "easy", "Easy"

    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="review_logs")
    card = models.ForeignKey(ReviewCard, on_delete=models.PROTECT, related_name="logs", blank=True, null=True)
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
