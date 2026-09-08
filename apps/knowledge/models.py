from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q
from django.utils.text import slugify


def normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def concept_attachment_path(instance, filename: str) -> str:
    """Keep private uploads independent from a user-controlled filename."""
    suffix = Path(filename).suffix.lower()
    return f"private/concepts/{instance.concept_id}/{uuid4().hex}{suffix}"


class OwnedSlugModel(models.Model):
    slug = models.SlugField(max_length=180, allow_unicode=True)

    class Meta:
        abstract = True

    def set_slug(self, source: str) -> None:
        base = slugify(source, allow_unicode=True) or "concept"
        candidate, number = base, 2
        queryset = type(self).objects.filter(owner=self.owner).exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            candidate = f"{base}-{number}"
            number += 1
        self.slug = candidate


class Category(OwnedSlugModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories")
    title = models.CharField(max_length=120)
    parent = models.ForeignKey(
        "self", blank=True, null=True, on_delete=models.PROTECT, related_name="children"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "slug"], name="knowledge_category_owner_slug_unique"),
            models.UniqueConstraint(
                fields=["owner", "title"],
                condition=Q(parent__isnull=True),
                name="knowledge_root_category_title_unique",
            ),
            models.UniqueConstraint(
                fields=["owner", "parent", "title"],
                condition=Q(parent__isnull=False),
                name="knowledge_child_category_title_unique",
            ),
        ]
        indexes = [models.Index(fields=["owner", "title"])]

    def clean(self):
        if not self.parent_id:
            return
        if self.parent_id == self.pk:
            raise ValidationError({"parent": "A category cannot be its own parent."})
        if self.parent.owner_id != self.owner_id:
            raise ValidationError({"parent": "Choose one of your own categories."})
        ancestor = self.parent
        while ancestor:
            if ancestor.pk == self.pk:
                raise ValidationError({"parent": "That parent would create a category cycle."})
            ancestor = ancestor.parent

    def save(self, *args, **kwargs):
        if not self.slug:
            self.set_slug(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Tag(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=60)
    normalized_name = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["owner", "normalized_name"], name="knowledge_tag_unique")]
        indexes = [models.Index(fields=["owner", "normalized_name"])]

    def save(self, *args, **kwargs):
        self.name = " ".join(self.name.split())
        self.normalized_name = normalized(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Concept(OwnedSlugModel):
    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="concepts")
    category = models.ForeignKey(
        Category, blank=True, null=True, on_delete=models.SET_NULL, related_name="concepts"
    )
    title = models.CharField(max_length=180)
    quick_definition = models.TextField()
    simple_explanation = models.TextField(blank=True)
    deep_dive = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.INTERMEDIATE)
    is_favorite = models.BooleanField(default=False)
    sync_version = models.PositiveIntegerField(default=1)
    tags = models.ManyToManyField(Tag, blank=True, related_name="concepts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["owner", "slug"], name="knowledge_concept_owner_slug_unique")]
        indexes = [
            models.Index(fields=["owner", "title"]),
            models.Index(fields=["owner", "-updated_at"]),
            models.Index(fields=["owner", "difficulty"]),
            models.Index(fields=["owner", "is_favorite"]),
        ]

    def clean(self):
        if self.category_id and self.category.owner_id != self.owner_id:
            raise ValidationError({"category": "Choose one of your own categories."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.set_slug(self.title)
        if self.pk and not self._state.adding:
            self.sync_version += 1
            if update_fields := kwargs.get("update_fields"):
                kwargs["update_fields"] = set(update_fields) | {"sync_version", "updated_at"}
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ConceptAlias(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="aliases")
    value = models.CharField(max_length=180)
    normalized_value = models.CharField(max_length=180)

    class Meta:
        ordering = ["value"]
        constraints = [models.UniqueConstraint(fields=["concept", "normalized_value"], name="knowledge_alias_unique")]
        indexes = [models.Index(fields=["normalized_value"])]

    def save(self, *args, **kwargs):
        self.value = " ".join(self.value.split())
        self.normalized_value = normalized(self.value)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.value


class CodeSnippet(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="snippets")
    title = models.CharField(max_length=120, blank=True)
    language = models.CharField(
        max_length=32, default="plaintext", validators=[RegexValidator(r"^[a-z0-9+.#_-]+$")]
    )
    code = models.TextField()
    explanation = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "pk"]

    def save(self, *args, **kwargs):
        self.language = self.language.strip().lower() or "plaintext"
        super().save(*args, **kwargs)


class CommonMistake(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="mistakes")
    title = models.CharField(max_length=160)
    description = models.TextField()
    correction = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]


class ConceptRelation(models.Model):
    class Type(models.TextChoices):
        RELATED = "related", "Related"
        PREREQUISITE = "prerequisite", "Prerequisite"
        EXTENDS = "extends", "Extends"
        CONTRASTS = "contrasts", "Contrasts"
        EXAMPLE_OF = "example_of", "Example of"

    source = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="outgoing_relations")
    target = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="incoming_relations")
    relation_type = models.CharField(max_length=20, choices=Type.choices, default=Type.RELATED)

    class Meta:
        ordering = ["target__title"]
        constraints = [
            models.UniqueConstraint(fields=["source", "target", "relation_type"], name="knowledge_relation_unique"),
            models.CheckConstraint(condition=~Q(source=F("target")), name="knowledge_relation_not_self"),
        ]

    def clean(self):
        if self.source_id == self.target_id:
            raise ValidationError({"target": "A concept cannot relate to itself."})
        if self.source_id and self.target_id and self.source.owner_id != self.target.owner_id:
            raise ValidationError({"target": "Choose one of your own concepts."})


class ConceptAttachment(models.Model):
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=concept_attachment_path)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return self.original_name

    @property
    def is_image(self):
        return self.content_type in {"image/jpeg", "image/png", "image/webp", "image/gif"}
