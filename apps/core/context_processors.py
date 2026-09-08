from django.conf import settings
from django.utils import timezone


def pwa(request):
    context = {"pwa_enabled": settings.PWA_ENABLED, "offline_knowledge_enabled": settings.OFFLINE_KNOWLEDGE_ENABLED, "review_due_count": 0}
    if request.user.is_authenticated:
        from apps.reviews.selectors import due_count

        context["review_due_count"] = due_count(request.user, timezone.now())
    return context
