"""Compact content snapshots; learning schedules and files are intentionally excluded."""

from datetime import date

from django.db import transaction

from apps.reviews.models import ReviewCard

from .models import Category, ConceptAlias, ConceptContext, ConceptRevision, ConceptSection, ConceptSource, Tag, normalized


def snapshot(concept):
    return {
        "title": concept.title, "quick_definition": concept.quick_definition,
        "simple_explanation": concept.simple_explanation, "deep_dive": concept.deep_dive,
        "difficulty": concept.difficulty, "category_id": concept.category_id,
        "freshness_status": concept.freshness_status,
        "last_verified_at": concept.last_verified_at.isoformat() if concept.last_verified_at else None,
        "verification_note": concept.verification_note,
        "tags": list(concept.tags.values_list("name", flat=True)),
        "aliases": list(concept.aliases.values_list("value", flat=True)),
        "sections": [{**row, "public_id": str(row["public_id"])} for row in concept.sections.values("public_id", "title", "section_type", "content", "sort_order")],
        "sources": list(concept.sources.values("title", "source_type", "url", "author", "publisher", "version", "note", "sort_order")),
        "contexts": list(concept.contexts.values("technology", "version", "note", "sort_order")),
        "cards": [{**row, "public_id": str(row["public_id"])} for row in concept.review_cards.values("public_id", "card_type", "question", "answer", "hint", "sort_order", "is_active")],
    }


def create_revision(concept, source):
    data = snapshot(concept)
    latest = concept.revisions.first()
    if latest and latest.snapshot == data:
        return latest
    return ConceptRevision.objects.create(concept=concept, revision_number=(latest.revision_number + 1 if latest else 1), snapshot=data, source=source)


@transaction.atomic
def restore_revision(concept, revision):
    """Restore content only; card schedules, logs, and attachment files stay untouched."""
    data = revision.snapshot
    concept.title = data["title"]
    concept.quick_definition = data["quick_definition"]
    concept.simple_explanation = data.get("simple_explanation", "")
    concept.deep_dive = data.get("deep_dive", "")
    concept.difficulty = data["difficulty"]
    concept.freshness_status = data.get("freshness_status", concept.Freshness.NEEDS_VERIFICATION)
    concept.last_verified_at = date.fromisoformat(data["last_verified_at"]) if data.get("last_verified_at") else None
    concept.verification_note = data.get("verification_note", "")
    concept.category_id = data.get("category_id") if Category.objects.filter(owner=concept.owner, pk=data.get("category_id")).exists() else None
    concept.set_slug(concept.title)
    concept.full_clean()
    concept.save()
    tags = [Tag.objects.get_or_create(owner=concept.owner, normalized_name=normalized(name), defaults={"name": name})[0] for name in data.get("tags", [])]
    concept.tags.set(tags)
    concept.aliases.all().delete()
    ConceptAlias.objects.bulk_create([ConceptAlias(concept=concept, value=value, normalized_value=normalized(value)) for value in data.get("aliases", [])])
    concept.sections.all().delete()
    ConceptSection.objects.bulk_create([ConceptSection(concept=concept, public_id=row["public_id"], title=row["title"], section_type=row["section_type"], content=row.get("content", ""), sort_order=row.get("sort_order", 0)) for row in data.get("sections", [])])
    concept.sources.all().delete()
    ConceptSource.objects.bulk_create([ConceptSource(concept=concept, **{key: row.get(key, "") for key in ("title", "source_type", "url", "author", "publisher", "version", "note", "sort_order")}) for row in data.get("sources", [])])
    concept.contexts.all().delete()
    ConceptContext.objects.bulk_create([ConceptContext(concept=concept, **{key: row.get(key, "") for key in ("technology", "version", "note", "sort_order")}) for row in data.get("contexts", [])])
    cards = {str(card.public_id): card for card in concept.review_cards.all()}
    revision_card_ids = set()
    for row in data.get("cards", []):
        if row["card_type"] == ReviewCard.Type.CONCEPT_RECALL:
            continue
        public_id = str(row["public_id"])
        revision_card_ids.add(public_id)
        card = cards.get(public_id)
        if card:
            card.question, card.answer, card.hint = row.get("question", ""), row.get("answer", ""), row.get("hint", "")
            card.sort_order, card.is_active = row.get("sort_order", 0), row.get("is_active", True)
            card.save(update_fields=["question", "answer", "hint", "sort_order", "is_active", "updated_at"])
        else:
            # Recreated historical cards begin inactive; no old schedule is fabricated.
            ReviewCard.objects.create(concept=concept, public_id=public_id, card_type=ReviewCard.Type.BASIC, question=row.get("question", ""), answer=row.get("answer", ""), hint=row.get("hint", ""), sort_order=row.get("sort_order", 0), is_active=False)
    for public_id, card in cards.items():
        if card.card_type == ReviewCard.Type.BASIC and public_id not in revision_card_ids and card.is_active:
            card.is_active = False
            card.save(update_fields=["is_active", "updated_at"])
    return create_revision(concept, "restore")
