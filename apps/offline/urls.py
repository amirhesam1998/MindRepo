from django.urls import path

from . import views


app_name = "offline"
urlpatterns = [
    path("settings/offline/", views.OfflineSettingsView.as_view(), name="settings"),
    path("offline/bootstrap/", views.bootstrap, name="bootstrap"),
    path("offline/changes/", views.changes, name="changes"),
    path("offline/mutations/", views.mutations, name="mutations"),
]
