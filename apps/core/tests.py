import json

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from .views import DashboardView


class DashboardTests(TestCase):
    def test_dashboard_route_resolves(self):
        self.assertIs(resolve(reverse("core:dashboard")).func.view_class, DashboardView)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("core:dashboard"))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next=/")

    def test_user_can_switch_between_english_and_persian(self):
        user = get_user_model().objects.create_user(username="language", password="password-123")
        self.client.force_login(user)
        response = self.client.post(reverse("set_language"), {"language": "fa", "next": reverse("core:dashboard")})
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertContains(self.client.get(reverse("core:dashboard")), "داشبورد")
        response = self.client.post(reverse("set_language"), {"language": "en", "next": reverse("core:dashboard")})
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertContains(self.client.get(reverse("core:dashboard")), "Dashboard")

    def test_analytics_and_health(self):
        user = get_user_model().objects.create_user(username="metrics", password="password-123")
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("core:analytics")), "Analytics")
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.json(), {"status": "ok"})


class PwaDeliveryTests(TestCase):
    def test_manifest_is_valid_json_with_icon_references(self):
        response = self.client.get(reverse("core:manifest"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/manifest+json"))
        manifest = json.loads(response.content)
        self.assertEqual(manifest["name"], "MindRepo — Developer Knowledge")
        self.assertEqual(len(manifest["icons"]), 3)
        self.assertTrue(all(icon["src"].startswith("/static/icons/") for icon in manifest["icons"]))
        self.assertIsNotNone(finders.find("icons/icon-192.png"))
        self.assertIsNotNone(finders.find("icons/icon-512.png"))

    def test_service_worker_is_javascript_at_root_scope(self):
        response = self.client.get(reverse("core:service_worker"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/javascript"))
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        self.assertContains(response, 'const CACHE_NAME = "mindrepo-static-v4";')
        self.assertContains(response, "/static/js/offline.js")
        self.assertContains(response, 'if (event.request.mode === "navigate")')
        self.assertContains(response, 'if (!STATIC_ASSETS.includes(url.pathname)) return;')
        self.assertNotContains(response, '"/library/"')

    def test_offline_page_is_public(self):
        response = self.client.get(reverse("core:offline"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You're offline")

    @override_settings(PWA_ENABLED=True)
    def test_layout_exposes_pwa_registration_flag_when_enabled(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertContains(response, 'data-pwa-enabled="true"')
