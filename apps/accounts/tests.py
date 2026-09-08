from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import resolve, reverse

from apps.core.views import DashboardView

from .views import MindRepoLoginView


class UserModelTests(TestCase):
    def test_user_creation(self):
        user = get_user_model().objects.create_user(username="ada", password="secure-pass-123")

        self.assertEqual(user.username, "ada")
        self.assertTrue(user.check_password("secure-pass-123"))

    def test_superuser_creation(self):
        user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="secure-pass-123"
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class AuthenticationTests(TestCase):
    def setUp(self):
        self.password = "secure-pass-123"
        self.user = get_user_model().objects.create_user(username="ada", password=self.password)

    def test_login_route_resolves(self):
        self.assertIs(resolve(reverse("accounts:login")).func.view_class, MindRepoLoginView)

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_correct_credentials_log_in_and_redirect_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": self.user.username, "password": self.password}
        )

        self.assertRedirects(response, reverse("core:dashboard"))

    def test_incorrect_credentials_are_rejected(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": self.user.username, "password": "wrong-password"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_authenticated_user_can_access_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/dashboard.html")
        self.assertIs(resolve(reverse("core:dashboard")).func.view_class, DashboardView)

    def test_logout_requires_post_and_ends_session(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse("accounts:logout"))
        response = self.client.post(reverse("accounts:logout"))

        self.assertEqual(get_response.status_code, 405)
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_is_temporarily_throttled_after_repeated_failures(self):
        cache.clear()
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": self.user.username, "password": "wrong"})
        response = self.client.post(reverse("accounts:login"), {"username": self.user.username, "password": self.password})
        self.assertContains(response, "Please wait a few minutes")
