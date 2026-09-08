from django.apps import AppConfig


class OfflineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.offline"

    def ready(self):
        from . import signals  # noqa: F401
