import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from apps.knowledge.models import Concept

from .models import OfflineChange
from .serializers import concept_document, sync_queryset
from .services import MAX_BATCH_SIZE, PROTOCOL_VERSION, apply_mutation, json_response


SYNC_PAGE_SIZE = 100


def _require_offline_knowledge_enabled():
    if not settings.OFFLINE_KNOWLEDGE_ENABLED:
        raise Http404


def _protocol_ok(request):
    try:
        version = int(request.GET.get("protocol_version", ""))
    except ValueError:
        version = None
    if version != PROTOCOL_VERSION:
        return json_response({"status": "upgrade_required", "required_protocol": PROTOCOL_VERSION, "full_resync_required": True}, status=400)


class OfflineSettingsView(LoginRequiredMixin, TemplateView):
    template_name = "offline/settings.html"

    def dispatch(self, request, *args, **kwargs):
        _require_offline_knowledge_enabled()
        return super().dispatch(request, *args, **kwargs)


@login_required
@require_GET
def bootstrap(request):
    _require_offline_knowledge_enabled()
    if response := _protocol_ok(request):
        return response
    try:
        after = max(0, int(request.GET.get("after", "0")))
        snapshot_cursor = request.GET.get("cursor")
        snapshot_cursor = int(snapshot_cursor) if snapshot_cursor is not None else None
    except ValueError:
        return HttpResponseBadRequest("Invalid cursor.")
    if snapshot_cursor is not None and snapshot_cursor < 0:
        return HttpResponseBadRequest("Invalid cursor.")
    # Anchor the whole paged snapshot before reading concepts. Changes after this
    # cursor are replayed by /offline/changes/ and cannot be skipped mid-bootstrap.
    if snapshot_cursor is None:
        snapshot_cursor = OfflineChange.objects.filter(owner=request.user).order_by("-pk").values_list("pk", flat=True).first() or 0
    concepts = list(sync_queryset(Concept.objects.filter(owner=request.user, pk__gt=after).order_by("pk"))[:SYNC_PAGE_SIZE])
    if request.GET.get("meta") == "1":
        return json_response(
            {
                "protocol_version": PROTOCOL_VERSION,
                "account_key": str(request.user.pk),
                "snapshot_cursor": snapshot_cursor,
            }
        )
    return json_response(
        {
            "protocol_version": PROTOCOL_VERSION,
            "account_key": str(request.user.pk),
            "snapshot_cursor": snapshot_cursor,
            "concepts": [concept_document(concept) for concept in concepts],
            "has_more": len(concepts) == SYNC_PAGE_SIZE,
            "next_after": concepts[-1].pk if concepts else after,
        }
    )


@login_required
@require_GET
def changes(request):
    _require_offline_knowledge_enabled()
    if response := _protocol_ok(request):
        return response
    try:
        cursor = int(request.GET.get("cursor", "0"))
    except ValueError:
        return json_response({"status": "full_resync", "message": "Invalid sync cursor."}, status=400)
    if cursor < 0:
        return json_response({"status": "full_resync", "message": "Invalid sync cursor."}, status=400)
    records = list(OfflineChange.objects.filter(owner=request.user, pk__gt=cursor).order_by("pk")[:SYNC_PAGE_SIZE])
    ids = [record.entity_id for record in records if record.operation == OfflineChange.Operation.UPSERT]
    concepts = {item.pk: item for item in sync_queryset(Concept.objects.filter(owner=request.user, pk__in=ids))}
    changes_payload = []
    for record in records:
        change = {"cursor": record.pk, "operation": record.operation, "entity_id": record.entity_id, "version": record.entity_version}
        if record.operation == OfflineChange.Operation.UPSERT and record.entity_id in concepts:
            change["entity"] = concept_document(concepts[record.entity_id])
        else:
            change["operation"] = OfflineChange.Operation.DELETE
        changes_payload.append(change)
    return json_response({"protocol_version": PROTOCOL_VERSION, "changes": changes_payload, "has_more": len(records) == SYNC_PAGE_SIZE, "next_cursor": records[-1].pk if records else cursor})


@login_required
@require_POST
def mutations(request):
    _require_offline_knowledge_enabled()
    try:
        payload = json.loads(request.body)
    except (TypeError, json.JSONDecodeError):
        return json_response({"message": "Invalid JSON."}, status=400)
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        return json_response({"status": "upgrade_required", "required_protocol": PROTOCOL_VERSION, "full_resync_required": True, "message": "Refresh MindRepo before syncing."}, status=400)
    mutations_list = payload.get("mutations")
    if not isinstance(mutations_list, list) or not mutations_list:
        return json_response({"message": "Mutations are required."}, status=400)
    if len(mutations_list) > MAX_BATCH_SIZE:
        return json_response({"message": "Too many mutations."}, status=400)
    results = []
    for mutation in mutations_list:
        if not isinstance(mutation, dict):
            results.append({"status": "invalid", "message": "Invalid mutation payload."})
            continue
        result = apply_mutation(user=request.user, mutation=mutation)
        if mutation.get("client_mutation_id") and "client_mutation_id" not in result:
            result["client_mutation_id"] = str(mutation["client_mutation_id"])
        results.append(result)
    status = 409 if any(result["status"] in {"conflict", "deleted_on_server"} for result in results) else 200
    return json_response({"protocol_version": PROTOCOL_VERSION, "results": results}, status=status)
