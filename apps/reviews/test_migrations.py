from datetime import timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class PopulatedLegacyReviewMigrationTests(TransactionTestCase):
    """Proves the staged card migration preserves non-default legacy review data."""

    migrate_from = [("knowledge", "0005_concept_freshness_status_concept_last_verified_at_and_more"), ("reviews", "0001_initial")]
    migrate_to = [("knowledge", "0005_concept_freshness_status_concept_last_verified_at_and_more"), ("reviews", "0003_migrate_concept_reviews_to_default_cards")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        User = old_apps.get_model("accounts", "User")
        Concept = old_apps.get_model("knowledge", "Concept")
        State = old_apps.get_model("reviews", "ConceptReviewState")
        Log = old_apps.get_model("reviews", "ReviewLog")
        user = User.objects.create(username="legacy-reviewer", password="unused")
        concept = Concept.objects.create(owner_id=user.pk, title="Legacy LINQ", quick_definition="Legacy definition", difficulty="intermediate")
        due = timezone.now().replace(microsecond=0) + timedelta(days=42)
        State.objects.create(concept_id=concept.pk, status="review", due_at=due, review_count=17, lapse_count=3, success_streak=6, interval_days=42, version=9, scheduler_data={"ease": 2.5})
        for offset, rating in enumerate(("again", "good", "easy")):
            Log.objects.create(concept_id=concept.pk, rating=rating, reviewed_at=due - timedelta(days=offset + 4), previous_status="review", new_status="review", previous_due_at=due - timedelta(days=offset + 1), new_due_at=due, previous_interval_days=21, new_interval_days=42, scheduler_version="mindrepo-v1")
        self.concept_id, self.due = concept.pk, due
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)

    def tearDown(self):
        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
        super().tearDown()

    def test_populated_legacy_state_and_logs_move_to_one_default_card(self):
        apps = MigrationExecutor(connection).loader.project_state(self.migrate_to).apps
        Card = apps.get_model("reviews", "ReviewCard")
        CardState = apps.get_model("reviews", "ReviewCardState")
        LegacyState = apps.get_model("reviews", "ConceptReviewState")
        Log = apps.get_model("reviews", "ReviewLog")
        card = Card.objects.get(concept_id=self.concept_id, card_type="concept_recall")
        state = CardState.objects.get(card_id=card.pk)
        legacy = LegacyState.objects.get(concept_id=self.concept_id)
        self.assertEqual(Card.objects.filter(concept_id=self.concept_id, card_type="concept_recall").count(), 1)
        self.assertEqual((state.status, state.due_at, state.review_count, state.lapse_count, state.success_streak, state.interval_days, state.version, state.scheduler_data), ("review", self.due, 17, 3, 6, 42, 9, {"ease": 2.5}))
        self.assertEqual((legacy.status, legacy.due_at, legacy.review_count), (state.status, state.due_at, state.review_count))
        self.assertEqual(Log.objects.filter(concept_id=self.concept_id).count(), 3)
        self.assertEqual(Log.objects.filter(concept_id=self.concept_id, card_id=card.pk).count(), 3)
