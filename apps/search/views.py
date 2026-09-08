import random
from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.views.generic import ListView, TemplateView

from apps.knowledge.models import Category, Concept, Tag

from .selectors import PALETTE_RESULT_LIMIT, filter_concepts, normalize_search_query, search_concepts


def request_filters(request):
    return {
        "category": request.GET.get("category"),
        "tag": request.GET.get("tag"),
        "difficulty": request.GET.get("difficulty"),
        "favorite": request.GET.get("favorite") == "1",
    }


class DiscoveryMixin(LoginRequiredMixin):
    def filter_context(self, context):
        context["categories"] = Category.objects.filter(owner=self.request.user)
        context["tags"] = Tag.objects.filter(owner=self.request.user)
        context["difficulty_choices"] = Concept.Difficulty.choices
        return context


class SearchView(DiscoveryMixin, ListView):
    template_name = "search/search.html"
    context_object_name = "concepts"
    paginate_by = 20

    def get_queryset(self):
        self.query = normalize_search_query(self.request.GET.get("q", ""))
        self.filters = request_filters(self.request)
        if not self.query:
            return Concept.objects.none()
        results = search_concepts(user=self.request.user, query=self.query, filters=self.filters)
        if self.request.GET.get("sort") == "updated":
            return results.order_by("-updated_at", "pk")
        if self.request.GET.get("sort") == "title":
            return results.order_by("title", "pk")
        return results

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.filter_context(context)
        context["query"] = self.query
        query = self.request.GET.copy()
        query.pop("page", None)
        context["filter_query"] = urlencode(query)
        return context


class PaletteView(LoginRequiredMixin, TemplateView):
    template_name = "search/partials/palette_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = normalize_search_query(self.request.GET.get("q", ""))
        context["query"] = query
        context["concepts"] = search_concepts(user=self.request.user, query=query, limit=PALETTE_RESULT_LIMIT) if query else []
        return context


class FavoritesView(DiscoveryMixin, ListView):
    template_name = "search/favorites.html"
    context_object_name = "concepts"
    paginate_by = 20

    def get_queryset(self):
        self.filters = request_filters(self.request)
        self.filters["favorite"] = True
        return (
            filter_concepts(Concept.objects.filter(owner=self.request.user), user=self.request.user, filters=self.filters)
            .select_related("category", "review_state")
            .prefetch_related("tags")
            .order_by("-updated_at", "pk")
            .distinct()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.filter_context(context)
        query = self.request.GET.copy()
        query.pop("page", None)
        context["filter_query"] = urlencode(query)
        return context


class RandomRecallView(DiscoveryMixin, TemplateView):
    template_name = "search/random.html"

    def get_eligible_concepts(self):
        return filter_concepts(Concept.objects.filter(owner=self.request.user), user=self.request.user, filters=request_filters(self.request))

    def get_concept(self):
        eligible = self.get_eligible_concepts()
        if concept_id := self.request.GET.get("concept"):
            try:
                return eligible.select_related("category", "review_state").prefetch_related("tags").get(pk=concept_id)
            except (Concept.DoesNotExist, ValueError) as error:
                raise Http404 from error
        previous = self.request.GET.get("previous")
        if previous and eligible.exclude(pk=previous).exists():
            eligible = eligible.exclude(pk=previous)
        count = eligible.count()
        if not count:
            return None
        # ponytail: offset selection is sufficient for personal libraries; sample primary keys if this becomes large.
        return eligible.select_related("category", "review_state").prefetch_related("tags").order_by("pk")[random.randrange(count)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.filter_context(context)
        context["concept"] = self.get_concept()
        context["revealed"] = self.request.GET.get("reveal") == "1"
        filters = self.request.GET.copy()
        for key in ["concept", "previous", "reveal", "partial"]:
            filters.pop(key, None)
        context["random_filters_query"] = urlencode(filters)
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if request.headers.get("HX-Request") == "true":
            return render(request, "search/partials/random_card.html", context)
        return self.render_to_response(context)
