from django.urls import path

from . import views


app_name = "search"

urlpatterns = [
    path("search/", views.SearchView.as_view(), name="search"),
    path("search/palette/", views.PaletteView.as_view(), name="palette"),
    path("favorites/", views.FavoritesView.as_view(), name="favorites"),
    path("random/", views.RandomRecallView.as_view(), name="random"),
]
