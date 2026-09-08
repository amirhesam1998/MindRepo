from django.urls import path

from . import views


app_name = "reviews"

urlpatterns = [
    path("review/", views.ReviewLandingView.as_view(), name="landing"),
    path("review/session/", views.ReviewSessionView.as_view(), name="session"),
    path("review/<int:state_id>/reveal/", views.RevealAnswerView.as_view(), name="reveal"),
    path("review/<int:state_id>/rate/", views.RateReviewView.as_view(), name="rate"),
    path("review/history/", views.ReviewHistoryView.as_view(), name="history"),
]
