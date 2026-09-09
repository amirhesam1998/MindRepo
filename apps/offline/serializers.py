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
        "freshness_status": concept.freshness_status,
        "last_verified_at": concept.last_verified_at.isoformat() if concept.last_verified_at else None,
        "verification_note": concept.verification_note,
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
        "sections": [
            {"id": item.pk, "title": item.title, "section_type": item.section_type, "content": item.content}
            for item in concept.sections.all()
        ],
        "sources": [
            {"id": item.pk, "title": item.title, "source_type": item.source_type, "url": item.url, "note": item.note}
            for item in concept.sources.all()
        ],
        "contexts": [
            {"technology": item.technology, "version": item.version, "note": item.note}
            for item in concept.contexts.all()
        ],
        "relations": [
            {"target_id": item.target_id, "target_title": item.target.title, "relation_type": item.relation_type}
            for item in concept.outgoing_relations.all()
        ],
    }


def sync_queryset(queryset):
    return queryset.select_related("category").prefetch_related(
        "tags", "aliases", "snippets", "mistakes", "sections", "sources", "contexts", "outgoing_relations__target"
    )
