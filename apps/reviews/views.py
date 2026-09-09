from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from .forms import RatingForm
from .models import ReviewCardState, ReviewLog
from .scheduling import interval_label, schedule
from .selectors import build_review_queue, due_count, new_count, next_due, reviewed_today_count
from .services import StaleReviewError, submit_review


SESSION_KEY = "mindrepo_review_session"


def session_data(request):
    return request.session.setdefault(SESSION_KEY, {"reviewed": 0, "ratings": {}, "initial": 0, "revealed": None})


class ReviewLandingView(LoginRequiredMixin, TemplateView):
    template_name = "reviews/landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        context.update(
            due_count=due_count(self.request.user, now),
            new_count=new_count(self.request.user, now),
            reviewed_today=reviewed_today_count(self.request.user, now),
            next_due=next_due(self.request.user, now),
        )
        return context


class ReviewSessionView(LoginRequiredMixin, TemplateView):
    template_name = "reviews/session.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        manual_id = self.request.GET.get("concept")
        queue = build_review_queue(self.request.user, now, manual_concept_id=manual_id)
        data = session_data(self.request)
        if self.request.GET.get("start") == "1" or manual_id:
            data = {"reviewed": 0, "ratings": {}, "initial": len(queue), "revealed": None}
            self.request.session[SESSION_KEY] = data
        state = queue[0] if queue else None
        revealed = bool(state and data.get("revealed") == [state.pk, state.version])
        previews = []
        if state and revealed:
            for rating, label in ReviewLog.Rating.choices:
                result = schedule(state, rating, now)
                previews.append((rating, label, interval_label(result, now)))
        reviewed = data.get("reviewed", 0)
        context.update(
            state=state,
            revealed=revealed,
            previews=previews,
            progress_current=reviewed + 1 if state else reviewed,
            progress_total=max(data.get("initial", 0), reviewed + len(queue)),
            remaining=len(queue),
            summary=data,
        )
        return context


class RevealAnswerView(LoginRequiredMixin, View):
    def post(self, request, state_id):
        state = ReviewCardState.objects.filter(pk=state_id, card__concept__owner=request.user, card__is_active=True).select_related("card", "card__concept").first()
        if not state:
            raise Http404
        try:
            version = int(request.POST.get("version", ""))
        except ValueError:
            version = -1
        if state.version != version:
            messages.warning(request, "That review card changed. Please continue with the current card.")
        else:
            data = session_data(request)
            data["revealed"] = [state.pk, state.version]
            request.session[SESSION_KEY] = data
        return HttpResponseRedirect(reverse("reviews:session"))


class RateReviewView(LoginRequiredMixin, View):
    def post(self, request, state_id):
        data = session_data(request)
        form = RatingForm(request.POST)
        state = ReviewCardState.objects.filter(pk=state_id, card__concept__owner=request.user, card__is_active=True).select_related("card", "card__concept").first()
        if not state:
            raise Http404
        if not form.is_valid() or data.get("revealed") != [state.pk, state.version]:
            messages.error(request, "Reveal the current answer before choosing a rating.")
            return HttpResponseRedirect(reverse("reviews:session"))
        try:
            submit_review(
                user=request.user,
                state_id=state.pk,
                rating=form.cleaned_data["rating"],
                version=form.cleaned_data["version"],
                reviewed_at=timezone.now(),
            )
        except StaleReviewError:
            messages.warning(request, "That review was already handled in another tab.")
        else:
            data["reviewed"] = data.get("reviewed", 0) + 1
            ratings = data.setdefault("ratings", {})
            rating = form.cleaned_data["rating"]
            ratings[rating] = ratings.get(rating, 0) + 1
            data["revealed"] = None
            request.session[SESSION_KEY] = data
        return HttpResponseRedirect(reverse("reviews:session"))


class ReviewHistoryView(LoginRequiredMixin, ListView):
    model = ReviewLog
    template_name = "reviews/history.html"
    context_object_name = "logs"
    paginate_by = 30

    def get_queryset(self):
        queryset = ReviewLog.objects.filter(Q(card__concept__owner=self.request.user) | Q(card__isnull=True, concept__owner=self.request.user)).select_related("concept", "card")
        if rating := self.request.GET.get("rating"):
            if rating in ReviewLog.Rating.values:
                queryset = queryset.filter(rating=rating)
        if concept_id := self.request.GET.get("concept"):
            queryset = queryset.filter(concept_id=concept_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ratings"] = ReviewLog.Rating.choices
        context["filter_query"] = self.request.GET.urlencode().replace("page=", "")
        return context
