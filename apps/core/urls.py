from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline, name="offline"),
    path("health/", views.health, name="health"),
    path("analytics/", views.AnalyticsView.as_view(), name="analytics"),
    path("", views.DashboardView.as_view(), name="dashboard"),
]
