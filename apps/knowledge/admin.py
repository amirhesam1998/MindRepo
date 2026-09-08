from django.contrib import admin

from .models import Category, CodeSnippet, CommonMistake, Concept, ConceptAlias, ConceptRelation, Tag


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
