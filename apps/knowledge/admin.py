from django.contrib import admin

from .models import Category, CodeSnippet, CommonMistake, Concept, ConceptAlias, ConceptAttachment, ConceptContext, ConceptRelation, ConceptRevision, ConceptSection, ConceptSource, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "parent", "updated_at")
    list_filter = ("owner",)
    search_fields = ("title", "description")


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "difficulty", "is_favorite", "updated_at")
    list_filter = ("difficulty", "is_favorite", "owner")
    search_fields = ("title", "quick_definition")
    filter_horizontal = ("tags",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name",)


admin.site.register(ConceptAlias)
admin.site.register(CodeSnippet)
admin.site.register(CommonMistake)
admin.site.register(ConceptRelation)


@admin.register(ConceptAttachment)
class ConceptAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "concept", "content_type", "file_size", "created_at")
    readonly_fields = ("original_name", "content_type", "file_size", "created_at")


admin.site.register(ConceptSection)
admin.site.register(ConceptSource)
admin.site.register(ConceptContext)


@admin.register(ConceptRevision)
class ConceptRevisionAdmin(admin.ModelAdmin):
    list_display = ("concept", "revision_number", "source", "created_at")
    readonly_fields = ("concept", "revision_number", "snapshot", "source", "created_at")
