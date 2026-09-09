import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse

from apps.knowledge.models import Category, Concept

from .models import AppliedClientMutation
from .serializers import concept_document, sync_queryset


OFFLINE_SYNC_PROTOCOL_VERSION = 2
PROTOCOL_VERSION = OFFLINE_SYNC_PROTOCOL_VERSION
MAX_BATCH_SIZE = 20


def mutation_error(message, *, fields=None):
    return {"status": "invalid", "message": message, "fields": fields or {}}


def apply_mutation(*, user, mutation):
    try:
        mutation_id = uuid.UUID(str(mutation["client_mutation_id"]))
        operation = mutation["operation"]
    except (KeyError, ValueError, TypeError):
        return mutation_error("Invalid mutation identifier or operation.")
    existing = AppliedClientMutation.objects.filter(owner=user, client_mutation_id=mutation_id).first()
    if existing:
        return existing.result

    payload = mutation.get("payload") or {}
    entity_id = mutation.get("entity_id")
    base_version = mutation.get("base_version")
    force = mutation.get("force") is True
    with transaction.atomic():
        if operation == "create":
            title = str(payload.get("title", "")).strip()
            quick_definition = str(payload.get("quick_definition", "")).strip()
            if not title or not quick_definition:
                return mutation_error("Title and quick definition are required.")
            concept = Concept(owner=user, title=title, quick_definition=quick_definition)
            concept.set_slug(title)
            for field in ["simple_explanation", "deep_dive", "difficulty", "is_favorite"]:
                if field in payload:
                    setattr(concept, field, payload[field])
            if category_id := payload.get("category_id"):
                concept.category = Category.objects.filter(owner=user, pk=category_id).first()
                if not concept.category:
                    return mutation_error("Choose one of your own categories.", fields={"category": "Invalid category."})
            try:
                concept.full_clean()
            except ValidationError as error:
                return mutation_error("Concept validation failed.", fields=error.message_dict)
            concept.save()
        else:
            concept = Concept.objects.filter(owner=user, pk=entity_id).first()
            if not concept:
                return {"status": "deleted_on_server", "entity_id": entity_id}
            if base_version != concept.sync_version and not force:
                return {"status": "conflict", "entity_id": concept.pk, "server": concept_document(sync_queryset(Concept.objects.filter(pk=concept.pk)).get()), "server_version": concept.sync_version}
            if operation == "favorite":
                concept.is_favorite = bool(payload.get("is_favorite"))
            elif operation == "update":
                for field in ["title", "quick_definition", "simple_explanation", "deep_dive", "difficulty", "is_favorite"]:
                    if field in payload:
                        setattr(concept, field, payload[field])
                if "category_id" in payload:
                    category_id = payload["category_id"]
                    concept.category = Category.objects.filter(owner=user, pk=category_id).first() if category_id else None
                    if category_id and not concept.category:
                        return mutation_error("Choose one of your own categories.", fields={"category": "Invalid category."})
            else:
                return mutation_error("Unsupported mutation operation.")
            try:
                concept.full_clean()
            except ValidationError as error:
                return mutation_error("Concept validation failed.", fields=error.message_dict)
            concept.save()
        document = concept_document(sync_queryset(Concept.objects.filter(pk=concept.pk)).get())
        result = {"status": "applied", "client_mutation_id": str(mutation_id), "entity": document}
        AppliedClientMutation.objects.create(owner=user, client_mutation_id=mutation_id, result=result)
        return result


def json_response(payload, *, status=200):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response
