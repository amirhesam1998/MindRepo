from django.contrib import admin

from .models import ConceptReviewState, ReviewLog


@admin.register(ConceptReviewState)
class ConceptReviewStateAdmin(admin.ModelAdmin):
    list_display = ("concept", "status", "due_at", "review_count", "lapse_count", "interval_days")
    list_filter = ("status",)
    search_fields = ("concept__title", "concept__owner__username")


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ("concept", "rating", "reviewed_at", "previous_interval_days", "new_interval_days")
    list_filter = ("rating",)
    search_fields = ("concept__title", "concept__owner__username")
    readonly_fields = [field.name for field in ReviewLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
