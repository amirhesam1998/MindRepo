from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.offline.urls")),
    path("", include("apps.search.urls")),
    path("", include("apps.reviews.urls")),
    path("", include("apps.knowledge.urls")),
    path("", include("apps.core.urls")),
]

handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
