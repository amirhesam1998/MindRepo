from django.urls import path

from . import views


app_name = "knowledge"

urlpatterns = [
    path("library/", views.LibraryView.as_view(), name="library"),
    path("library/new/", views.ConceptCreateView.as_view(), name="concept_create"),
    path("library/<int:pk>/<str:slug>/", views.ConceptDetailView.as_view(), name="concept_detail"),
    path("library/<int:pk>/<str:slug>/edit/", views.ConceptUpdateView.as_view(), name="concept_edit"),
    path("library/<int:pk>/<str:slug>/delete/", views.ConceptDeleteView.as_view(), name="concept_delete"),
    path("library/<int:pk>/<str:slug>/favorite/", views.FavoriteToggleView.as_view(), name="concept_favorite"),
    path("library/<int:pk>/<str:slug>/attachments/<int:attachment_pk>/", views.AttachmentDownloadView.as_view(), name="attachment_download"),
    path("library/categories/", views.CategoryListView.as_view(), name="category_list"),
    path("library/categories/new/", views.CategoryCreateView.as_view(), name="category_create"),
    path("library/categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("library/categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
    path("settings/data/", views.DataSettingsView.as_view(), name="data_settings"),
    path("settings/data/export.json", views.export_json_view, name="export_json"),
    path("settings/data/export.zip", views.export_markdown_view, name="export_markdown"),
]
