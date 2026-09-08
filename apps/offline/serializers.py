from apps.knowledge.models import Concept


def concept_document(concept: Concept) -> dict:
    return {
        "id": concept.pk,
        "slug": concept.slug,
        "title": concept.title,
        "quick_definition": concept.quick_definition,
        "simple_explanation": concept.simple_explanation,
        "deep_dive": concept.deep_dive,
        "difficulty": concept.difficulty,
        "is_favorite": concept.is_favorite,
        "sync_version": concept.sync_version,
        "updated_at": concept.updated_at.isoformat(),
        "category": ({"id": concept.category_id, "title": concept.category.title} if concept.category_id else None),
        "tags": [{"id": tag.pk, "name": tag.name} for tag in concept.tags.all()],
        "aliases": [alias.value for alias in concept.aliases.all()],
        "snippets": [
            {"id": item.pk, "title": item.title, "language": item.language, "code": item.code, "explanation": item.explanation}
            for item in concept.snippets.all()
        ],
        "mistakes": [
            {"id": item.pk, "title": item.title, "description": item.description, "correction": item.correction}
            for item in concept.mistakes.all()
        ],
        "relations": [
            {"target_id": item.target_id, "target_title": item.target.title, "relation_type": item.relation_type}
            for item in concept.outgoing_relations.all()
        ],
    }


def sync_queryset(queryset):
    return queryset.select_related("category").prefetch_related(
        "tags", "aliases", "snippets", "mistakes", "outgoing_relations__target"
    )
