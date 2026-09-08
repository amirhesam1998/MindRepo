from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        from apps.knowledge.models import Category, Concept
        from apps.reviews.selectors import due_count, new_count, reviewed_today_count
        from django.utils import timezone

        context = super().get_context_data(**kwargs)
        concepts = Concept.objects.filter(owner=self.request.user)
        now = timezone.now()
        context.update(
            concept_count=concepts.count(),
            category_count=Category.objects.filter(owner=self.request.user).count(),
            favorite_count=concepts.filter(is_favorite=True).count(),
            recent_concepts=concepts.select_related("category")[:5],
            due_review_count=due_count(self.request.user, now),
            new_review_count=new_count(self.request.user, now),
            reviewed_today_count=reviewed_today_count(self.request.user, now),
        )
        return context


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "core/analytics.html"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def get_context_data(self, **kwargs):
        from .analytics import analytics_for_user

        context = super().get_context_data(**kwargs)
        context["analytics"] = analytics_for_user(self.request.user, self.request.GET.get("window", "30"))
        return context


def error_403(request, exception):
    return render(request, "403.html", status=403)


def error_404(request, exception):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)


@require_GET
def manifest(request):
    return HttpResponse(
        render_to_string("pwa/manifest.webmanifest", request=request),
        content_type="application/manifest+json",
    )


@require_GET
def service_worker(request):
    response = HttpResponse(
        render_to_string("pwa/service-worker.js", request=request),
        content_type="application/javascript",
    )
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
def offline(request):
    return render(request, "pwa/offline.html")


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})
