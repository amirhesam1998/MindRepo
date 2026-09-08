from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.knowledge.models import Concept

from .models import ConceptReviewState, ReviewLog
from .scheduling import MAX_INTERVAL_DAYS, schedule
from .selectors import build_review_queue, mastery_level
from .services import StaleReviewError, submit_review


class ReviewTestCase(TestCase):
    def setUp(self):
        self.now = timezone.now().replace(microsecond=0)
        self.user = get_user_model().objects.create_user(username="reviewer", password="password-123")
        self.other = get_user_model().objects.create_user(username="other-reviewer", password="password-123")
        self.client.force_login(self.user)

    def state(self, title="Dependency Injection", **kwargs):
        concept = Concept.objects.create(owner=self.user, title=title, quick_definition="Dependencies come from outside.")
        state = concept.review_state
        for field, value in kwargs.items():
            setattr(state, field, value)
        state.save()
        return state


class SchedulerTests(ReviewTestCase):
    def test_new_rating_intervals_are_deterministic_and_ordered(self):
        state = self.state(status=ConceptReviewState.Status.NEW, due_at=self.now)
        results = {rating: schedule(state, rating, self.now) for rating in ReviewLog.Rating.values}

        self.assertEqual(results["again"].status, ConceptReviewState.Status.LEARNING)
        self.assertLess(results["again"].due_at, results["hard"].due_at)
        self.assertLess(results["hard"].due_at, results["good"].due_at)
        self.assertLess(results["good"].due_at, results["easy"].due_at)
        self.assertEqual(results["good"], schedule(state, "good", self.now))

    def test_learning_and_relearning_handle_all_ratings(self):
        for status in [ConceptReviewState.Status.LEARNING, ConceptReviewState.Status.RELEARNING]:
            state = self.state(title=status, status=status, due_at=self.now)
            results = [schedule(state, rating, self.now) for rating in ReviewLog.Rating.values]
            self.assertEqual(results[0].status, status)
            self.assertEqual(results[2].status, ConceptReviewState.Status.REVIEW)
            self.assertEqual(results[3].status, ConceptReviewState.Status.REVIEW)

    def test_review_lapse_relearning_and_interval_bounds(self):
        state = self.state(status=ConceptReviewState.Status.REVIEW, interval_days=100, success_streak=4, due_at=self.now)
        again = schedule(state, "again", self.now)
        hard = schedule(state, "hard", self.now)
        good = schedule(state, "good", self.now)
        easy = schedule(state, "easy", self.now)

        self.assertEqual(again.status, ConceptReviewState.Status.RELEARNING)
        self.assertEqual(again.lapse_delta, 1)
        self.assertLess(hard.interval_days, good.interval_days)
        self.assertLess(good.interval_days, easy.interval_days)
        state.interval_days = MAX_INTERVAL_DAYS
        self.assertLessEqual(schedule(state, "easy", self.now).interval_days, MAX_INTERVAL_DAYS)

    def test_mastery_is_qualitative_and_derived(self):
        state = self.state(status=ConceptReviewState.Status.NEW, due_at=self.now)
        self.assertEqual(mastery_level(state), "New")
        state.status = ConceptReviewState.Status.LEARNING
        self.assertEqual(mastery_level(state), "Learning")
        state.status, state.interval_days, state.success_streak = ConceptReviewState.Status.REVIEW, 7, 2
        self.assertEqual(mastery_level(state), "Familiar")
        state.interval_days, state.success_streak = 21, 3
        self.assertEqual(mastery_level(state), "Strong")


class ReviewDomainTests(ReviewTestCase):
    def test_new_concept_gets_exactly_one_review_state(self):
        state = self.state()
        self.assertEqual(state.status, ConceptReviewState.Status.NEW)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConceptReviewState.objects.create(concept=state.concept, due_at=self.now)

    def test_submission_updates_state_and_writes_immutable_history(self):
        state = self.state(due_at=self.now)
        updated = submit_review(user=self.user, state_id=state.pk, rating="good", version=0, reviewed_at=self.now)
        log = ReviewLog.objects.get(concept=state.concept)

        self.assertEqual(updated.status, ConceptReviewState.Status.REVIEW)
        self.assertEqual(updated.review_count, 1)
        self.assertEqual(log.previous_status, ConceptReviewState.Status.NEW)
        self.assertEqual(log.new_interval_days, updated.interval_days)
        with self.assertRaises(StaleReviewError):
            submit_review(user=self.user, state_id=state.pk, rating="good", version=0, reviewed_at=self.now)

    def test_queue_prioritizes_overdue_then_due_then_new_and_respects_users(self):
        overdue = self.state("Overdue", status=ConceptReviewState.Status.REVIEW, due_at=self.now - timedelta(days=2))
        due = self.state("Due", status=ConceptReviewState.Status.REVIEW, due_at=self.now)
        new_one = self.state("New one", status=ConceptReviewState.Status.NEW, due_at=self.now)
        self.state("Future", status=ConceptReviewState.Status.REVIEW, due_at=self.now + timedelta(days=1))
        foreign = Concept.objects.create(owner=self.other, title="Foreign", quick_definition="Private")
        queue = build_review_queue(self.user, self.now, new_limit=1)

        self.assertEqual([item.pk for item in queue], [overdue.pk, due.pk, new_one.pk])
        self.assertNotIn(foreign.review_state.pk, [item.pk for item in queue])

    def test_queue_includes_due_boundary_and_limits_new_cards(self):
        due = self.state("Due boundary", status=ConceptReviewState.Status.REVIEW, due_at=self.now)
        first_new = self.state("First new", status=ConceptReviewState.Status.NEW, due_at=self.now)
        self.state("Second new", status=ConceptReviewState.Status.NEW, due_at=self.now)
        self.state("Future", status=ConceptReviewState.Status.REVIEW, due_at=self.now + timedelta(seconds=1))

        queue = build_review_queue(self.user, self.now, new_limit=1)
        self.assertEqual([item.pk for item in queue], [due.pk, first_new.pk])


class ReviewHttpTests(ReviewTestCase):
    def test_review_session_reveals_then_rates_and_history_is_private(self):
        state = self.state(due_at=self.now)
        session_url = f"{reverse('reviews:session')}?start=1"
        initial = self.client.get(session_url)
        self.assertContains(initial, "Show Answer")
        self.assertNotContains(initial, state.concept.quick_definition)

        self.client.post(reverse("reviews:reveal", args=[state.pk]), {"version": state.version})
        revealed = self.client.get(reverse("reviews:session"))
        self.assertContains(revealed, state.concept.quick_definition)
        self.assertContains(revealed, "Again")

        response = self.client.post(reverse("reviews:rate", args=[state.pk]), {"version": state.version, "rating": "good"})
        self.assertRedirects(response, reverse("reviews:session"))
        self.assertEqual(ReviewLog.objects.count(), 1)
        self.assertContains(self.client.get(reverse("reviews:history")), state.concept.title)

        foreign = Concept.objects.create(owner=self.other, title="Foreign", quick_definition="Private")
        self.assertEqual(self.client.post(reverse("reviews:rate", args=[foreign.review_state.pk]), {"version": 0, "rating": "good"}).status_code, 404)

    def test_review_navigation_dashboard_and_invalid_rating(self):
        state = self.state(status=ConceptReviewState.Status.REVIEW, due_at=self.now)
        dashboard = self.client.get(reverse("core:dashboard"))
        landing = self.client.get(reverse("reviews:landing"))
        self.assertContains(dashboard, "Start Review")
        self.assertContains(landing, "Due now")

        self.client.get(f"{reverse('reviews:session')}?start=1")
        self.client.post(reverse("reviews:reveal", args=[state.pk]), {"version": state.version})
        response = self.client.post(reverse("reviews:rate", args=[state.pk]), {"version": state.version, "rating": "perfect"})
        self.assertRedirects(response, reverse("reviews:session"))
        self.assertEqual(ReviewLog.objects.count(), 0)

    def test_review_routes_require_authentication_and_dashboard_counts_real_reviews(self):
        state = self.state(due_at=self.now)
        submit_review(user=self.user, state_id=state.pk, rating="good", version=0, reviewed_at=self.now)
        dashboard = self.client.get(reverse("core:dashboard"))
        self.assertEqual(dashboard.context["reviewed_today_count"], 1)
        self.assertContains(dashboard, "1 reviewed today")

        self.client.logout()
        response = self.client.get(reverse("reviews:landing"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_history_paginates_and_excludes_other_users(self):
        state = self.state()
        ReviewLog.objects.bulk_create(
            [
                ReviewLog(
                    concept=state.concept,
                    rating="good",
                    reviewed_at=self.now - timedelta(minutes=index),
                    previous_status="new",
                    new_status="review",
                    previous_due_at=self.now,
                    new_due_at=self.now + timedelta(days=3),
                    previous_interval_days=0,
                    new_interval_days=3,
                )
                for index in range(31)
            ]
        )
        foreign = Concept.objects.create(owner=self.other, title="Foreign log", quick_definition="Private")
        ReviewLog.objects.create(
            concept=foreign,
            rating="good",
            reviewed_at=self.now,
            previous_status="new",
            new_status="review",
            previous_due_at=self.now,
            new_due_at=self.now + timedelta(days=3),
            previous_interval_days=0,
            new_interval_days=3,
        )

        response = self.client.get(reverse("reviews:history"))
        self.assertEqual(response.context["paginator"].count, 31)
        self.assertContains(response, state.concept.title)
        self.assertNotContains(response, foreign.title)
