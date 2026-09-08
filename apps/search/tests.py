from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.knowledge.models import Category, Concept, ConceptAlias, Tag
from apps.reviews.models import ReviewLog

from .selectors import PALETTE_RESULT_LIMIT, search_concepts


class DiscoveryTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="discoverer", password="password-123")
        self.other = get_user_model().objects.create_user(username="private", password="password-123")
        self.client.force_login(self.user)

    def concept(self, title="Dependency Injection", **kwargs):
        defaults = {"owner": self.user, "quick_definition": "Dependencies are supplied from outside."}
        defaults.update(kwargs)
        return Concept.objects.create(title=title, **defaults)


class SearchSelectorTests(DiscoveryTestCase):
    def test_searches_title_alias_tag_category_and_content_once(self):
        category = Category.objects.create(owner=self.user, title="Architecture")
        concept = self.concept(
            category=category,
            simple_explanation="Constructor coupling becomes explicit.",
            deep_dive="The dependency is supplied by a composition root.",
        )
        ConceptAlias.objects.create(concept=concept, value="DI")
        tag = Tag.objects.create(owner=self.user, name="SOLID")
        concept.tags.add(tag)

        for query in ["dependency injection", "DI", "solid", "architecture", "constructor coupling", "composition root"]:
            self.assertEqual(list(search_concepts(user=self.user, query=query)), [concept])

    def test_search_is_case_insensitive_and_handles_technical_and_persian_variants(self):
        cpp = self.concept("C++", quick_definition="A systems language.")
        node = self.concept("Node.js", quick_definition="JavaScript runtime.")
        persian = self.concept("تزريق وابستگي", quick_definition="Definition")

        self.assertEqual(list(search_concepts(user=self.user, query="c++")), [cpp])
        self.assertEqual(list(search_concepts(user=self.user, query="NODE.JS")), [node])
        self.assertEqual(list(search_concepts(user=self.user, query="تزریق وابستگی")), [persian])

    def test_exact_title_beats_deep_content_and_other_users_are_excluded(self):
        exact = self.concept("SOLID", deep_dive="Short definition")
        deep_match = self.concept("Architecture notes", deep_dive="SOLID is mentioned only in deep content.")
        private = Concept.objects.create(owner=self.other, title="SOLID", quick_definition="Private")

        results = list(search_concepts(user=self.user, query="solid"))
        self.assertEqual(results[0], exact)
        self.assertIn(deep_match, results)
        self.assertNotIn(private, results)

    def test_search_filters_are_owner_scoped(self):
        category = Category.objects.create(owner=self.user, title="Backend")
        tag = Tag.objects.create(owner=self.user, name="Python")
        included = self.concept(category=category, difficulty="advanced", is_favorite=True)
        included.tags.add(tag)
        self.concept("Other concept", difficulty="beginner")

        results = search_concepts(
            user=self.user,
            query="dependencies",
            filters={"category": category.pk, "tag": tag.pk, "difficulty": "advanced", "favorite": True},
        )
        self.assertEqual(list(results), [included])


class SearchHttpTests(DiscoveryTestCase):
    def test_search_page_palette_limit_and_library_delegate_to_shared_search(self):
        concept = self.concept()
        ConceptAlias.objects.create(concept=concept, value="DI")
        for index in range(PALETTE_RESULT_LIMIT + 2):
            self.concept(f"DI helper {index}")

        response = self.client.get(reverse("search:search"), {"q": "DI"})
        self.assertContains(response, concept.title)
        self.assertContains(self.client.get(reverse("knowledge:library"), {"query": "DI"}), concept.title)
        palette = self.client.get(reverse("search:palette"), {"q": "DI"})
        self.assertEqual(palette.status_code, 200)
        self.assertLessEqual(palette.content.count(b"data-palette-result"), PALETTE_RESULT_LIMIT)

    def test_search_and_palette_require_authentication_and_escape_query(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("search:search")).status_code, 302)
        self.assertEqual(self.client.get(reverse("search:palette")).status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse("search:search"), {"q": "<script>alert(1)</script>"})
        self.assertNotContains(response, "<script>alert(1)</script>", html=True)


class FavoriteTests(DiscoveryTestCase):
    def test_owner_can_toggle_favorite_with_htmx_and_favorites_are_private(self):
        concept = self.concept()
        url = reverse("knowledge:concept_favorite", args=[concept.pk, concept.slug])
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, HTTP_HX_REQUEST="true")
        concept.refresh_from_db()
        self.assertTrue(concept.is_favorite)
        self.assertContains(response, "Remove from favorites")
        self.client.post(url)
        concept.refresh_from_db()
        self.assertFalse(concept.is_favorite)

        concept.is_favorite = True
        concept.save(update_fields=["is_favorite"])
        foreign = Concept.objects.create(owner=self.other, title="Private favorite", quick_definition="Private", is_favorite=True)
        favorites = self.client.get(reverse("search:favorites"))
        self.assertContains(favorites, concept.title)
        self.assertNotContains(favorites, foreign.title)
        self.assertEqual(
            self.client.post(reverse("knowledge:concept_favorite", args=[foreign.pk, foreign.slug])).status_code,
            404,
        )


class RandomRecallTests(DiscoveryTestCase):
    def test_random_recall_is_owner_scoped_and_does_not_mutate_reviews(self):
        first = self.concept("First")
        second = self.concept("Second")
        first_state = first.review_state
        before = (first_state.version, first_state.due_at, ReviewLog.objects.count())

        response = self.client.get(reverse("search:random"), {"concept": first.pk, "reveal": 1})
        self.assertContains(response, first.quick_definition)
        first_state.refresh_from_db()
        self.assertEqual((first_state.version, first_state.due_at, ReviewLog.objects.count()), before)
        next_response = self.client.get(reverse("search:random"), {"previous": first.pk})
        self.assertEqual(next_response.context["concept"], second)

        private = Concept.objects.create(owner=self.other, title="Private", quick_definition="Private")
        self.assertEqual(self.client.get(reverse("search:random"), {"concept": private.pk}).status_code, 404)

    def test_random_filters_and_empty_state(self):
        category = Category.objects.create(owner=self.user, title="Database")
        favorite = self.concept("ACID", category=category, difficulty="advanced", is_favorite=True)
        self.concept("React", difficulty="beginner")
        response = self.client.get(
            reverse("search:random"),
            {"category": category.pk, "difficulty": "advanced", "favorite": 1},
        )
        self.assertEqual(response.context["concept"], favorite)

        self.client.logout()
        empty_user = get_user_model().objects.create_user(username="empty", password="password-123")
        self.client.force_login(empty_user)
        self.assertContains(self.client.get(reverse("search:random")), "Nothing to recall yet")
