from django.contrib.auth import get_user_model
import os
import tempfile
import zipfile
from io import BytesIO

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ConceptForm
from .models import Category, CodeSnippet, CommonMistake, Concept, ConceptAlias, ConceptAttachment, ConceptRelation, Tag
from .portability import apply_import, build_export, export_markdown_zip, validate_import


class KnowledgeTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner", password="password-123")
        self.other = get_user_model().objects.create_user(username="other", password="password-123")
        self.client.force_login(self.user)

    def concept(self, title="Dependency Injection", **kwargs):
        kwargs.setdefault("quick_definition", "Dependencies arrive from outside.")
        return Concept.objects.create(owner=self.user, title=title, **kwargs)


class CategoryTests(KnowledgeTestCase):
    def test_create_and_parent_category(self):
        root = Category.objects.create(owner=self.user, title="Programming")
        response = self.client.post(reverse("knowledge:category_create"), {"title": "Python", "parent": root.pk})

        self.assertRedirects(response, reverse("knowledge:category_list"))
        self.assertEqual(Category.objects.get(title="Python").parent, root)

    def test_category_rejects_self_and_indirect_cycle(self):
        root = Category.objects.create(owner=self.user, title="Root")
        child = Category.objects.create(owner=self.user, title="Child", parent=root)
        root.parent = child

        with self.assertRaises(ValidationError):
            root.full_clean()
        child.parent = child
        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_category_delete_blocks_children_or_concepts(self):
        category = Category.objects.create(owner=self.user, title="Backend")
        self.concept(category=category)

        response = self.client.post(reverse("knowledge:category_delete", args=[category.pk]), follow=True)

        self.assertTrue(Category.objects.filter(pk=category.pk).exists())
        self.assertContains(response, "Move child categories")

    def test_category_cross_user_urls_are_not_found(self):
        category = Category.objects.create(owner=self.other, title="Private")

        self.assertEqual(self.client.get(reverse("knowledge:category_edit", args=[category.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("knowledge:category_delete", args=[category.pk])).status_code, 404)


class ConceptTests(KnowledgeTestCase):
    @staticmethod
    def empty_formsets():
        return {
            "aliases-TOTAL_FORMS": 0, "aliases-INITIAL_FORMS": 0, "aliases-MIN_NUM_FORMS": 0, "aliases-MAX_NUM_FORMS": 1000,
            "snippets-TOTAL_FORMS": 0, "snippets-INITIAL_FORMS": 0, "snippets-MIN_NUM_FORMS": 0, "snippets-MAX_NUM_FORMS": 1000,
            "mistakes-TOTAL_FORMS": 0, "mistakes-INITIAL_FORMS": 0, "mistakes-MIN_NUM_FORMS": 0, "mistakes-MAX_NUM_FORMS": 1000,
            "outgoing_relations-TOTAL_FORMS": 0, "outgoing_relations-INITIAL_FORMS": 0, "outgoing_relations-MIN_NUM_FORMS": 0, "outgoing_relations-MAX_NUM_FORMS": 1000,
        }

    def test_minimal_concept_creation_and_dashboard_counts(self):
        data = {"title": "ACID", "quick_definition": "Transaction properties.", "difficulty": "intermediate", "tag_names": ""}
        data.update(self.empty_formsets())

        response = self.client.post(reverse("knowledge:concept_create"), data)

        concept = Concept.objects.get(title="ACID")
        self.assertRedirects(response, reverse("knowledge:concept_detail", args=[concept.pk, concept.slug]))
        dashboard = self.client.get(reverse("core:dashboard"))
        self.assertContains(dashboard, "1")
        self.assertContains(dashboard, "ACID")

    def test_editor_renders_progressive_enhancement_controls(self):
        response = self.client.get(reverse("knowledge:concept_create"))

        self.assertContains(response, "data-tag-editor")
        self.assertContains(response, "data-attachment-input")
        self.assertContains(response, "Add code example")

    def test_concept_form_rejects_another_users_category(self):
        category = Category.objects.create(owner=self.other, title="Private")
        form = ConceptForm(
            data={"title": "Unsafe", "quick_definition": "No", "difficulty": "beginner", "category": category.pk},
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_full_concept_creation_saves_related_records_atomically(self):
        category = Category.objects.create(owner=self.user, title="Architecture")
        target = self.concept("Inversion of Control")
        data = {
            "title": "Dependency Injection", "quick_definition": "Supply dependencies from outside.",
            "simple_explanation": "A class receives what it needs.", "deep_dive": "Constructor injection is explicit.",
            "category": category.pk, "difficulty": "advanced", "tag_names": "Python, Architecture",
            "aliases-TOTAL_FORMS": 1, "aliases-INITIAL_FORMS": 0, "aliases-MIN_NUM_FORMS": 0, "aliases-MAX_NUM_FORMS": 1000,
            "aliases-0-value": "DI",
            "snippets-TOTAL_FORMS": 1, "snippets-INITIAL_FORMS": 0, "snippets-MIN_NUM_FORMS": 0, "snippets-MAX_NUM_FORMS": 1000,
            "snippets-0-title": "Python", "snippets-0-language": "python", "snippets-0-code": "class Service: pass", "snippets-0-explanation": "Example", "snippets-0-sort_order": 0,
            "mistakes-TOTAL_FORMS": 1, "mistakes-INITIAL_FORMS": 0, "mistakes-MIN_NUM_FORMS": 0, "mistakes-MAX_NUM_FORMS": 1000,
            "mistakes-0-title": "Constructing dependencies", "mistakes-0-description": "Creates coupling", "mistakes-0-correction": "Inject them", "mistakes-0-sort_order": 0,
            "outgoing_relations-TOTAL_FORMS": 1, "outgoing_relations-INITIAL_FORMS": 0, "outgoing_relations-MIN_NUM_FORMS": 0, "outgoing_relations-MAX_NUM_FORMS": 1000,
            "outgoing_relations-0-target": target.pk, "outgoing_relations-0-relation_type": "related",
        }

        response = self.client.post(reverse("knowledge:concept_create"), data)

        concept = Concept.objects.get(title="Dependency Injection")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(concept.category, category)
        self.assertEqual(list(concept.tags.values_list("normalized_name", flat=True)), ["architecture", "python"])
        self.assertEqual(concept.aliases.get().value, "DI")
        self.assertEqual(concept.snippets.get().language, "python")
        self.assertEqual(concept.mistakes.get().correction, "Inject them")
        self.assertEqual(concept.outgoing_relations.get().target, target)

    def test_detail_edit_and_delete_are_owner_scoped(self):
        concept = Concept.objects.create(owner=self.other, title="Private", quick_definition="Private note")
        detail = reverse("knowledge:concept_detail", args=[concept.pk, concept.slug])

        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.get(reverse("knowledge:concept_edit", args=[concept.pk, concept.slug])).status_code, 404)
        self.assertEqual(self.client.post(reverse("knowledge:concept_delete", args=[concept.pk, concept.slug])).status_code, 404)

    def test_code_and_text_are_escaped_in_detail(self):
        concept = self.concept(quick_definition="<script>alert(1)</script>")
        CodeSnippet.objects.create(concept=concept, language="html", code="<img src=x onerror=alert(1)>")

        response = self.client.get(reverse("knowledge:concept_detail", args=[concept.pk, concept.slug]))

        self.assertNotContains(response, "<script>alert(1)</script>", html=True)
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;", html=False)
        self.assertContains(response, "&lt;img src=x onerror=alert(1)&gt;", html=False)

    def test_detail_prioritizes_quick_recall_and_mobile_add_is_a_real_link(self):
        concept = self.concept()
        response = self.client.get(reverse("knowledge:concept_detail", args=[concept.pk, concept.slug]))

        self.assertContains(response, "Quick recall")
        self.assertContains(response, reverse("knowledge:concept_create"))


class RelatedDataTests(KnowledgeTestCase):
    def test_tag_normalization_is_owner_scoped(self):
        first = Tag.objects.create(owner=self.user, name=" Django ")
        self.assertEqual(first.normalized_name, "django")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(owner=self.user, name="DJANGO")
        second = Tag.objects.create(owner=self.other, name="django")
        self.assertNotEqual(first.pk, second.pk)

    def test_alias_duplicate_is_prevented(self):
        concept = self.concept()
        ConceptAlias.objects.create(concept=concept, value="DI")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConceptAlias.objects.create(concept=concept, value=" di ")

    def test_snippet_and_mistake_belong_to_concept(self):
        concept = self.concept()
        snippet = CodeSnippet.objects.create(concept=concept, language="PYTHON", code="print('ok')")
        mistake = CommonMistake.objects.create(concept=concept, title="Manual construction", description="Coupling")

        self.assertEqual(snippet.language, "python")
        self.assertEqual(concept.snippets.get(), snippet)
        self.assertEqual(concept.mistakes.get(), mistake)

    def test_relations_are_directed_and_validate_ownership(self):
        source = self.concept("DI")
        target = self.concept("IoC")
        relation = ConceptRelation.objects.create(source=source, target=target)
        self.assertEqual(relation.target, target)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConceptRelation.objects.create(source=source, target=target)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConceptRelation.objects.create(source=source, target=source)
        foreign = Concept.objects.create(owner=self.other, title="Private", quick_definition="Private")
        invalid = ConceptRelation(source=source, target=foreign)
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_library_filters_title_alias_tag_and_difficulty(self):
        concept = self.concept("Dependency Injection", difficulty="advanced")
        tag = Tag.objects.create(owner=self.user, name="Architecture")
        concept.tags.add(tag)
        ConceptAlias.objects.create(concept=concept, value="DI")
        self.concept("ACID", difficulty="beginner")

        response = self.client.get(reverse("knowledge:library"), {"query": "DI", "tag": tag.pk, "difficulty": "advanced"})

        self.assertContains(response, "Dependency Injection")
        self.assertNotContains(response, ">ACID<", html=False)


class AttachmentTests(ConceptTests):
    def setUp(self):
        super().setUp()
        self.media = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media.name)
        self.media_settings.enable()

    def tearDown(self):
        self.media_settings.disable()
        self.media.cleanup()
        super().tearDown()

    def test_upload_detail_and_owner_scoped_download(self):
        data = {"title": "Diagram", "quick_definition": "A private file.", "difficulty": "beginner", "tag_names": "[]"}
        data.update(self.empty_formsets())
        data["attachments"] = SimpleUploadedFile("diagram.png", b"tiny image", content_type="image/png")
        response = self.client.post(reverse("knowledge:concept_create"), data)

        concept = Concept.objects.get(title="Diagram")
        attachment = concept.attachments.get()
        self.assertRedirects(response, reverse("knowledge:concept_detail", args=[concept.pk, concept.slug]))
        detail = self.client.get(reverse("knowledge:concept_detail", args=[concept.pk, concept.slug]))
        self.assertContains(detail, "diagram.png")
        url = reverse("knowledge:attachment_download", args=[concept.pk, concept.slug, attachment.pk])
        download = self.client.get(url)
        self.assertEqual(download.status_code, 200)
        download.close()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_attachment_validation_and_explicit_removal(self):
        data = {"title": "Unsafe", "quick_definition": "No executable upload.", "difficulty": "beginner", "tag_names": "[]"}
        data.update(self.empty_formsets())
        data["attachments"] = SimpleUploadedFile("unsafe.exe", b"no", content_type="application/octet-stream")
        response = self.client.post(reverse("knowledge:concept_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Concept.objects.filter(title="Unsafe").exists())

        concept = self.concept("Attached")
        attachment = ConceptAttachment.objects.create(concept=concept, file=SimpleUploadedFile("note.txt", b"note", content_type="text/plain"), original_name="note.txt", content_type="text/plain", file_size=4)
        path = attachment.file.path
        data = {"title": concept.title, "quick_definition": concept.quick_definition, "difficulty": concept.difficulty, "tag_names": "[]", "remove_attachment_ids": str(attachment.pk)}
        data.update(self.empty_formsets())
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("knowledge:concept_edit", args=[concept.pk, concept.slug]), data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConceptAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertFalse(os.path.exists(path))

    def test_concept_delete_cleans_private_attachment_file_after_commit(self):
        concept = self.concept("Delete attachment")
        attachment = ConceptAttachment.objects.create(concept=concept, file=SimpleUploadedFile("delete.txt", b"delete", content_type="text/plain"), original_name="delete.txt", content_type="text/plain", file_size=6)
        path = attachment.file.path
        with self.captureOnCommitCallbacks(execute=True):
            concept.delete()
        self.assertFalse(os.path.exists(path))

    def test_json_tags_and_sort_order_are_saved(self):
        data = {"title": "Tagged", "quick_definition": "Tag chips serialize JSON.", "difficulty": "beginner", "tag_names": '["Django", " django ", "Python"]'}
        data.update(self.empty_formsets())
        data.update({"snippets-TOTAL_FORMS": 2, "snippets-0-title": "Second", "snippets-0-language": "python", "snippets-0-code": "two", "snippets-0-sort_order": 1, "snippets-1-title": "First", "snippets-1-language": "python", "snippets-1-code": "one", "snippets-1-sort_order": 0})
        response = self.client.post(reverse("knowledge:concept_create"), data)
        concept = Concept.objects.get(title="Tagged")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(set(concept.tags.values_list("normalized_name", flat=True)), {"django", "python"})
        self.assertEqual(list(concept.snippets.values_list("title", flat=True)), ["First", "Second"])

    def test_existing_inline_item_can_be_removed_with_hidden_delete_field(self):
        concept = self.concept("Alias removal")
        alias = ConceptAlias.objects.create(concept=concept, value="DI")
        data = {"title": concept.title, "quick_definition": concept.quick_definition, "difficulty": concept.difficulty, "tag_names": "[]", "aliases-TOTAL_FORMS": 1, "aliases-INITIAL_FORMS": 1, "aliases-MIN_NUM_FORMS": 0, "aliases-MAX_NUM_FORMS": 1000, "aliases-0-id": alias.pk, "aliases-0-value": alias.value, "aliases-0-DELETE": "on"}
        data.update({key: value for key, value in self.empty_formsets().items() if not key.startswith("aliases-")})
        response = self.client.post(reverse("knowledge:concept_edit", args=[concept.pk, concept.slug]), data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ConceptAlias.objects.filter(pk=alias.pk).exists())

    def test_markdown_export_copies_sanitized_owned_attachment(self):
        concept = self.concept("Portable")
        ConceptAttachment.objects.create(
            concept=concept,
            file=SimpleUploadedFile("../../note.txt", b"portable", content_type="text/plain"),
            original_name="../../note.txt",
            content_type="text/plain",
            file_size=8,
        )

        with zipfile.ZipFile(BytesIO(export_markdown_zip(self.user))) as archive:
            names = archive.namelist()
        self.assertTrue(any(name.endswith("note.txt") for name in names))
        self.assertFalse(any(".." in name for name in names))


class PortabilityTests(KnowledgeTestCase):
    def test_export_is_owner_scoped_and_markdown_is_safe_zip(self):
        category = Category.objects.create(owner=self.user, title="Architecture")
        concept = self.concept("C++ / ../../escape", category=category)
        ConceptAlias.objects.create(concept=concept, value="CPP")
        payload = build_export(self.user)
        self.assertEqual(payload["format"], "mindrepo")
        self.assertEqual(len(payload["data"]["concepts"]), 1)
        self.assertNotIn("password", str(payload))
        archive = export_markdown_zip(self.user)
        self.assertTrue(archive.startswith(b"PK"))
        response = self.client.get(reverse("knowledge:export_json"))
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_import_preview_is_non_mutating_and_apply_maps_relations(self):
        first = self.concept("One")
        second = self.concept("Two")
        ConceptRelation.objects.create(source=first, target=second)
        payload = build_export(self.user)
        other = get_user_model().objects.create_user(username="importer", password="password-123")
        preview = validate_import(payload, other)
        self.assertEqual(preview["concepts"], 2)
        self.assertEqual(Concept.objects.filter(owner=other).count(), 0)
        result = apply_import(other, payload)
        self.assertEqual(result["concepts"], 2)
        self.assertEqual(ConceptRelation.objects.filter(source__owner=other).count(), 1)

    def test_import_rejects_duplicate_ids_and_invalid_relations_without_writes(self):
        payload = {"format": "mindrepo", "version": 1, "data": {"categories": [], "concepts": [{"id": "one", "title": "A", "quick_definition": "A", "difficulty": "beginner", "relations": ["broken"]}, {"id": "one", "title": "B", "quick_definition": "B", "difficulty": "beginner"}]}}
        with self.assertRaises(ValidationError):
            validate_import(payload, self.user)
        self.assertEqual(Concept.objects.filter(owner=self.user).count(), 0)

    def test_import_rejects_malformed_required_fields_and_duplicate_aliases(self):
        payload = {"format": "mindrepo", "version": 1, "data": {"categories": [], "concepts": [{"id": "one", "title": "A", "quick_definition": "A", "aliases": ["DI", " di "], "difficulty": "beginner"}, {"id": "two", "title": "B", "quick_definition": "B"}]}}
        with self.assertRaises(ValidationError):
            validate_import(payload, self.user)
        self.assertEqual(Concept.objects.filter(owner=self.user).count(), 0)

    def test_nested_form_edits_emit_a_final_sync_change(self):
        concept = self.concept()
        before = concept.sync_version
        data = {"title": concept.title, "quick_definition": concept.quick_definition, "difficulty": concept.difficulty, "tag_names": "", "aliases-TOTAL_FORMS": 1, "aliases-INITIAL_FORMS": 0, "aliases-MIN_NUM_FORMS": 0, "aliases-MAX_NUM_FORMS": 1000, "aliases-0-value": "DI", "snippets-TOTAL_FORMS": 0, "snippets-INITIAL_FORMS": 0, "snippets-MIN_NUM_FORMS": 0, "snippets-MAX_NUM_FORMS": 1000, "mistakes-TOTAL_FORMS": 0, "mistakes-INITIAL_FORMS": 0, "mistakes-MIN_NUM_FORMS": 0, "mistakes-MAX_NUM_FORMS": 1000, "outgoing_relations-TOTAL_FORMS": 0, "outgoing_relations-INITIAL_FORMS": 0, "outgoing_relations-MIN_NUM_FORMS": 0, "outgoing_relations-MAX_NUM_FORMS": 1000}
        self.client.post(reverse("knowledge:concept_edit", args=[concept.pk, concept.slug]), data)
        concept.refresh_from_db()
        self.assertGreater(concept.sync_version, before)
