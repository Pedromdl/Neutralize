from django.urls import path
from . import views
from .views import InstagramFeedView

urlpatterns = [
    # STRAVA
    path("strava/authorize/", views.strava_authorize, name="strava-authorize"),
    path("strava/callback/", views.strava_callback, name="strava-callback"),
    path("strava/status/", views.strava_status, name="strava-status"),
    path("strava/atividades/", views.strava_atividades, name="strava-atividades"),


    # INSTAGRAM
    path("instagram/", InstagramFeedView.as_view(), name="instagram-feed"),
]
