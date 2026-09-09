from django.db import migrations


def migrate_reviews(apps, schema_editor):
    Concept = apps.get_model("knowledge", "Concept")
    LegacyState = apps.get_model("reviews", "ConceptReviewState")
    ReviewCard = apps.get_model("reviews", "ReviewCard")
    ReviewCardState = apps.get_model("reviews", "ReviewCardState")
    ReviewLog = apps.get_model("reviews", "ReviewLog")
    for concept in Concept.objects.iterator():
        card, _ = ReviewCard.objects.get_or_create(
            concept_id=concept.pk,
            card_type="concept_recall",
            defaults={"sort_order": 0, "is_active": True},
        )
        state = LegacyState.objects.filter(concept_id=concept.pk).first()
        if state:
            ReviewCardState.objects.get_or_create(
                card_id=card.pk,
                defaults={
                    "status": state.status,
                    "due_at": state.due_at,
                    "last_reviewed_at": state.last_reviewed_at,
                    "review_count": state.review_count,
                    "lapse_count": state.lapse_count,
                    "success_streak": state.success_streak,
                    "interval_days": state.interval_days,
                    "version": state.version,
                    "scheduler_data": state.scheduler_data,
                },
            )
        else:
            ReviewCardState.objects.get_or_create(card_id=card.pk)
        ReviewLog.objects.filter(concept_id=concept.pk, card__isnull=True).update(card_id=card.pk)


class Migration(migrations.Migration):
    dependencies = [("reviews", "0002_reviewcard_reviewlog_card_reviewcardstate_and_more")]
    operations = [migrations.RunPython(migrate_reviews, migrations.RunPython.noop)]
