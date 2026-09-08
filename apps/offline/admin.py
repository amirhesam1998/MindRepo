from django.contrib import admin

from .models import AppliedClientMutation, OfflineChange


@admin.register(OfflineChange)
class OfflineChangeAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "entity_id", "operation", "entity_version", "created_at")
    list_filter = ("operation",)
    search_fields = ("owner__username", "entity_id")


@admin.register(AppliedClientMutation)
class AppliedClientMutationAdmin(admin.ModelAdmin):
    list_display = ("owner", "client_mutation_id", "applied_at")
    readonly_fields = ("owner", "client_mutation_id", "result", "applied_at")
    search_fields = ("owner__username", "client_mutation_id")
