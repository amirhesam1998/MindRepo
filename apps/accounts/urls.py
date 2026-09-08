from django.urls import path

from .views import MindRepoLoginView, MindRepoLogoutView


app_name = "accounts"

urlpatterns = [
    path("login/", MindRepoLoginView.as_view(), name="login"),
    path("logout/", MindRepoLogoutView.as_view(), name="logout"),
]
