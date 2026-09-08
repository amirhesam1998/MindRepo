import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.knowledge.models import Concept

from .models import OfflineChange


@override_settings(OFFLINE_KNOWLEDGE_ENABLED=True)
class OfflineSyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="offline", password="password-123")
        self.other = get_user_model().objects.create_user(username="other", password="password-123")
        self.client.force_login(self.user)

    def concept(self, title="Dependency Injection", **kwargs):
        return Concept.objects.create(owner=self.user, title=title, quick_definition="Dependencies come from outside.", **kwargs)

    def post_mutations(self, mutations):
        return self.client.post(
            reverse("offline:mutations"),
            data=json.dumps({"protocol_version": 1, "mutations": mutations}),
            content_type="application/json",
        )

    def test_bootstrap_and_changes_are_private_json_no_store(self):
        concept = self.concept()
        response = self.client.get(reverse("offline:bootstrap"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response.json()["concepts"][0]["id"], concept.pk)
        private = Concept.objects.create(owner=self.other, title="Private", quick_definition="Private")
        self.assertNotIn(private.pk, [item["id"] for item in response.json()["concepts"]])

        concept.quick_definition = "Updated"
        concept.save()
        changes = self.client.get(reverse("offline:changes"), {"cursor": 0}).json()["changes"]
        self.assertTrue(any(change["entity_id"] == concept.pk for change in changes))
        invalid = self.client.get(reverse("offline:changes"), {"cursor": -1})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["status"], "full_resync")

    def test_bootstrap_uses_the_supplied_snapshot_cursor(self):
        self.concept()
        cursor = OfflineChange.objects.order_by("-pk").first().pk
        self.concept("Later")
        response = self.client.get(reverse("offline:bootstrap"), {"cursor": cursor})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["snapshot_cursor"], cursor)

    @override_settings(OFFLINE_KNOWLEDGE_ENABLED=False)
    def test_offline_endpoints_are_hidden_when_the_feature_is_disabled(self):
        self.assertEqual(self.client.get(reverse("offline:settings")).status_code, 404)
        self.assertEqual(self.client.get(reverse("offline:bootstrap")).status_code, 404)
        self.assertEqual(self.client.get(reverse("offline:changes")).status_code, 404)
        self.assertEqual(self.post_mutations([]).status_code, 404)

    def test_delete_creates_tombstone_change(self):
        concept = self.concept()
        cursor = OfflineChange.objects.order_by("-pk").first().pk
        concept_id = concept.pk
        concept.delete()
        change = self.client.get(reverse("offline:changes"), {"cursor": cursor}).json()["changes"][0]
        self.assertEqual(change["operation"], "delete")
        self.assertEqual(change["entity_id"], concept_id)

    def test_create_update_and_favorite_mutations_are_idempotent(self):
        mutation_id = str(uuid.uuid4())
        create = {"client_mutation_id": mutation_id, "operation": "create", "payload": {"title": "Offline ACID", "quick_definition": "Transaction properties."}}
        first = self.post_mutations([create])
        self.assertEqual(first.status_code, 200)
        entity = first.json()["results"][0]["entity"]
        self.assertEqual(Concept.objects.filter(owner=self.user, title="Offline ACID").count(), 1)
        repeat = self.post_mutations([create])
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(Concept.objects.filter(owner=self.user, title="Offline ACID").count(), 1)

        favorite = {"client_mutation_id": str(uuid.uuid4()), "operation": "favorite", "entity_id": entity["id"], "base_version": entity["sync_version"], "payload": {"is_favorite": True}}
        applied = self.post_mutations([favorite]).json()["results"][0]
        self.assertTrue(applied["entity"]["is_favorite"])

    def test_stale_mutation_conflicts_without_overwriting_server(self):
        concept = self.concept()
        base = concept.sync_version
        concept.quick_definition = "Server version"
        concept.save()
        mutation = {"client_mutation_id": str(uuid.uuid4()), "operation": "update", "entity_id": concept.pk, "base_version": base, "payload": {"quick_definition": "Offline version"}}
        response = self.post_mutations([mutation])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["results"][0]["status"], "conflict")
        concept.refresh_from_db()
        self.assertEqual(concept.quick_definition, "Server version")

    def test_mutations_require_authentication_and_owner_scope(self):
        foreign = Concept.objects.create(owner=self.other, title="Private", quick_definition="Private")
        mutation = {"client_mutation_id": str(uuid.uuid4()), "operation": "favorite", "entity_id": foreign.pk, "base_version": foreign.sync_version, "payload": {"is_favorite": True}}
        response = self.post_mutations([mutation])
        self.assertEqual(response.json()["results"][0]["status"], "deleted_on_server")
        foreign.refresh_from_db()
        self.assertFalse(foreign.is_favorite)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("offline:bootstrap")).status_code, 302)
        self.assertEqual(self.post_mutations([mutation]).status_code, 302)

    def test_mutation_protocol_and_payload_are_validated(self):
        response = self.client.post(
            reverse("offline:mutations"),
            data=json.dumps({"protocol_version": 99, "mutations": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        malformed = self.post_mutations(["not-a-mutation"])
        self.assertEqual(malformed.status_code, 200)
        self.assertEqual(malformed.json()["results"][0]["status"], "invalid")

    def test_normal_online_favorite_generates_change_and_sync_version(self):
        concept = self.concept()
        version = concept.sync_version
        response = self.client.post(reverse("knowledge:concept_favorite", args=[concept.pk, concept.slug]))
        self.assertEqual(response.status_code, 302)
        concept.refresh_from_db()
        self.assertGreater(concept.sync_version, version)
        self.assertTrue(OfflineChange.objects.filter(owner=self.user, entity_id=concept.pk).exists())

    def test_normal_online_create_update_and_delete_are_sync_visible(self):
        concept = self.concept()
        created_cursor = OfflineChange.objects.order_by("-pk").first().pk
        concept.quick_definition = "Changed online"
        concept.save()
        update_changes = self.client.get(reverse("offline:changes"), {"cursor": created_cursor}).json()["changes"]
        self.assertTrue(any(change["entity_id"] == concept.pk and change["operation"] == "upsert" for change in update_changes))
        updated_cursor = OfflineChange.objects.order_by("-pk").first().pk
        concept_id = concept.pk
        concept.delete()
        changes = self.client.get(reverse("offline:changes"), {"cursor": updated_cursor}).json()["changes"]
        self.assertTrue(any(change["entity_id"] == concept_id and change["operation"] == "delete" for change in changes))
