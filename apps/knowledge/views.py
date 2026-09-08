from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.utils.formats import date_format
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    AliasFormSet,
    CategoryForm,
    ConceptForm,
    MistakeFormSet,
    RelationFormSet,
    SnippetFormSet,
)
from .models import Category, Concept, ConceptAttachment, ConceptRelation, Tag
from .portability import MAX_IMPORT_BYTES, apply_import, export_json, export_markdown_zip, validate_import


def category_rows(categories):
    """Return the small per-user adjacency list as (category, depth) rows."""
    children = {}
    for category in categories:
        children.setdefault(category.parent_id, []).append(category)
    rows = []

    def add_branch(parent_id, depth=0):
        for category in children.get(parent_id, []):
            rows.append((category, depth))
            add_branch(category.pk, depth + 1)

    add_branch(None)
    return rows


class LibraryView(LoginRequiredMixin, ListView):
    model = Concept
    template_name = "knowledge/library.html"
    context_object_name = "concepts"
    paginate_by = 20

    def get_queryset(self):
        filters = {
            "category": self.request.GET.get("category"),
            "tag": self.request.GET.get("tag"),
            "difficulty": self.request.GET.get("difficulty"),
            "favorite": self.request.GET.get("favorite") == "1",
        }
        queryset = (
            Concept.objects.filter(owner=self.request.user)
            .select_related("category", "review_state")
            .prefetch_related("tags")
        )
        query = self.request.GET.get("query", "").strip()
        if query:
            from apps.search.selectors import search_concepts

            return search_concepts(user=self.request.user, query=query, filters=filters)
        if category_id := filters["category"]:
            queryset = queryset.filter(category_id=category_id)
        if tag_id := filters["tag"]:
            queryset = queryset.filter(tags__id=tag_id)
        if difficulty := filters["difficulty"]:
            if difficulty in Concept.Difficulty.values:
                queryset = queryset.filter(difficulty=difficulty)
        if filters["favorite"]:
            queryset = queryset.filter(is_favorite=True)
        ordering = {"updated": "-updated_at", "newest": "-created_at", "title": "title"}
        return queryset.order_by(ordering.get(self.request.GET.get("sort"), "-updated_at"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(owner=self.request.user)
        context["tags"] = Tag.objects.filter(owner=self.request.user)
        query = self.request.GET.copy()
        query.pop("page", None)
        context["filter_query"] = urlencode(query)
        return context


class OwnedConceptMixin(LoginRequiredMixin):
    def get_queryset(self):
        return Concept.objects.filter(owner=self.request.user)

    def get_object(self, queryset=None):
        return get_object_or_404(queryset or self.get_queryset(), pk=self.kwargs["pk"], slug=self.kwargs["slug"])


class ConceptDetailView(OwnedConceptMixin, DetailView):
    template_name = "knowledge/concept_detail.html"
    context_object_name = "concept"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("category", "review_state")
            .prefetch_related(
                "tags",
                "aliases",
                "snippets",
                "mistakes",
                "attachments",
                Prefetch("outgoing_relations", queryset=ConceptRelation.objects.select_related("target")),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.reviews.models import ConceptReviewState
        from apps.reviews.selectors import mastery_level

        try:
            state = self.object.review_state
        except ConceptReviewState.DoesNotExist:
            state, _ = ConceptReviewState.objects.get_or_create(
                concept=self.object,
                defaults={"due_at": timezone.now()},
            )
        if state.status == ConceptReviewState.Status.NEW:
            review_status = "New"
        elif state.due_at <= timezone.now():
            review_status = "Due now"
        else:
            review_status = f"Due {date_format(state.due_at, 'M j')}"
        context["review_summary"] = {"state": state, "status": review_status, "mastery": mastery_level(state)}
        return context


class ConceptFormMixin(OwnedConceptMixin):
    form_class = ConceptForm
    template_name = "knowledge/concept_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_formsets(self, instance):
        kwargs = {"instance": instance}
        if self.request.method == "POST":
            kwargs.update({"data": self.request.POST})
        return {
            "aliases": AliasFormSet(**kwargs),
            "snippets": SnippetFormSet(**kwargs),
            "mistakes": MistakeFormSet(**kwargs),
            "relations": RelationFormSet(
                **kwargs,
                form_kwargs={"user": self.request.user},
            ),
        }

    @staticmethod
    def validate_attachments(files):
        allowed = {
            ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"}, ".png": {"image/png"},
            ".webp": {"image/webp"}, ".gif": {"image/gif"}, ".pdf": {"application/pdf"},
            ".txt": {"text/plain"}, ".md": {"text/plain", "text/markdown"},
        }
        limit = 10 * 1024 * 1024
        errors = []
        for upload in files:
            suffix = upload.name.lower().rsplit(".", 1)
            suffix = f".{suffix[-1]}" if len(suffix) == 2 else ""
            if suffix not in allowed or upload.size > limit:
                errors.append(upload.name)
                continue
            if upload.content_type and upload.content_type.lower() not in allowed[suffix]:
                errors.append(upload.name)
        if errors:
            raise ValidationError("Attachments must be JPG, PNG, WEBP, GIF, PDF, TXT, or Markdown files under 10 MB.")

    def save_attachments(self, concept):
        files = self.request.FILES.getlist("attachments")
        self.validate_attachments(files)
        removed = {value for value in self.request.POST.getlist("remove_attachment_ids") if value.isdigit()}
        if removed:
            ConceptAttachment.objects.filter(concept=concept, pk__in=removed).delete()
        next_order = concept.attachments.count()
        for upload in files:
            ConceptAttachment.objects.create(
                concept=concept,
                file=upload,
                original_name=upload.name[:255],
                content_type=upload.content_type[:100] or "application/octet-stream",
                file_size=upload.size,
                sort_order=next_order,
            )
            next_order += 1
        if files or removed:
            concept.save(update_fields=["updated_at"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = getattr(self, "object", None) or Concept(owner=self.request.user)
        context.setdefault("formsets", self.get_formsets(instance))
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if hasattr(self, "get_object") and kwargs else None
        form = self.get_form()
        formsets = self.get_formsets(self.object or Concept(owner=request.user))
        if form.is_valid() and all(formset.is_valid() for formset in formsets.values()):
            try:
                with transaction.atomic():
                    concept = form.save()
                    for formset in formsets.values():
                        formset.instance = concept
                        formset.save()
                    self.save_attachments(concept)
                    # Nested records are part of the offline Concept aggregate. Ensure a
                    # final aggregate version/change is visible after formset writes.
                    if any(formset.has_changed() for formset in formsets.values()):
                        concept.save(update_fields=["updated_at"])
            except ValidationError as error:
                form.add_error(None, error)
                return self.render_to_response(self.get_context_data(form=form, formsets=formsets))
            self.object = concept
            messages.success(request, "Concept saved.")
            return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form, formsets=formsets))

    def get_success_url(self):
        return reverse("knowledge:concept_detail", kwargs={"pk": self.object.pk, "slug": self.object.slug})


class ConceptCreateView(ConceptFormMixin, CreateView):
    def get_object(self):
        return None


class ConceptUpdateView(ConceptFormMixin, UpdateView):
    pass


class ConceptDeleteView(OwnedConceptMixin, DeleteView):
    template_name = "knowledge/concept_confirm_delete.html"
    context_object_name = "concept"
    success_url = reverse_lazy("knowledge:library")

    def form_valid(self, form):
        messages.success(self.request, "Concept deleted.")
        return super().form_valid(form)


class FavoriteToggleView(OwnedConceptMixin, View):
    def post(self, request, pk, slug):
        concept = self.get_object()
        concept.is_favorite = not concept.is_favorite
        concept.save(update_fields=["is_favorite"])
        if request.headers.get("HX-Request") == "true":
            return render(request, "partials/favorite_button.html", {"concept": concept})
        next_url = request.POST.get("next", "")
        if url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
            return HttpResponseRedirect(next_url)
        return HttpResponseRedirect(reverse("knowledge:concept_detail", args=[concept.pk, concept.slug]))


class AttachmentDownloadView(OwnedConceptMixin, View):
    def get(self, request, pk, slug, attachment_pk):
        concept = self.get_object()
        attachment = get_object_or_404(ConceptAttachment, pk=attachment_pk, concept=concept)
        inline_types = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}
        response = FileResponse(attachment.file.open("rb"), content_type=attachment.content_type)
        disposition = "inline" if request.GET.get("inline") == "1" and attachment.content_type in inline_types else "attachment"
        filename = attachment.original_name.replace("\r", "").replace("\n", "").replace(chr(34), "")
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = "knowledge/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user).select_related("parent")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_rows"] = category_rows(context["categories"])
        return context


class CategoryFormMixin(LoginRequiredMixin):
    model = Category
    form_class = CategoryForm
    template_name = "knowledge/category_form.html"

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("knowledge:category_list")


class CategoryCreateView(CategoryFormMixin, CreateView):
    def form_valid(self, form):
        messages.success(self.request, "Category saved.")
        return super().form_valid(form)


class CategoryUpdateView(CategoryFormMixin, UpdateView):
    def form_valid(self, form):
        messages.success(self.request, "Category saved.")
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = "knowledge/category_confirm_delete.html"
    success_url = reverse_lazy("knowledge:category_list")

    def get_queryset(self):
        return Category.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        category = self.get_object()
        if category.children.exists() or category.concepts.exists():
            messages.error(self.request, "Move child categories and concepts before deleting this category.")
            return HttpResponseRedirect(self.success_url)
        messages.success(self.request, "Category deleted.")
        return super().form_valid(form)


class DataSettingsView(LoginRequiredMixin, View):
    template_name = "knowledge/data_settings.html"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def get(self, request):
        return render(request, self.template_name, {"preview": request.session.get("mindrepo_import_preview")})

    def post(self, request):
        if request.POST.get("action") == "apply":
            payload = request.session.get("mindrepo_import_payload")
            if not payload:
                messages.error(request, "Upload an export file before importing.")
                return HttpResponseRedirect(reverse("knowledge:data_settings"))
            try:
                result = apply_import(request.user, payload, request.POST.get("strategy", "skip"))
            except Exception as error:
                messages.error(request, f"Import could not be applied: {error}")
                return HttpResponseRedirect(reverse("knowledge:data_settings"))
            request.session.pop("mindrepo_import_payload", None)
            request.session.pop("mindrepo_import_preview", None)
            messages.success(request, f"Imported {result['concepts']} concepts and {result['categories']} categories; skipped {result['skipped']} duplicates.")
            return HttpResponseRedirect(reverse("knowledge:data_settings"))
        upload = request.FILES.get("file")
        if not upload or upload.size > MAX_IMPORT_BYTES:
            messages.error(request, "Choose a MindRepo JSON export smaller than 2 MB.")
            return HttpResponseRedirect(reverse("knowledge:data_settings"))
        try:
            import json

            payload = json.loads(upload.read().decode("utf-8"))
            preview = validate_import(payload, request.user)
        except (UnicodeDecodeError, ValueError, ValidationError) as error:
            messages.error(request, f"Import validation failed: {error}")
            return HttpResponseRedirect(reverse("knowledge:data_settings"))
        request.session["mindrepo_import_payload"] = payload
        request.session["mindrepo_import_preview"] = preview
        return render(request, self.template_name, {"preview": preview})


def _download(content, content_type, filename):
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response


@login_required
@require_GET
def export_json_view(request):
    return _download(export_json(request.user), "application/json; charset=utf-8", "mindrepo-export.json")


@login_required
@require_GET
def export_markdown_view(request):
    return _download(export_markdown_zip(request.user), "application/zip", "mindrepo-markdown-export.zip")
