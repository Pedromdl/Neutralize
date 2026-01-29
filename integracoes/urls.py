from django.urls import path
from . import views
from .views import GoogleContactsStatusView, InstagramFeedView, google_contacts_connect, google_contacts_callback, google_contacts_disconnect

urlpatterns = [
    # STRAVA
    path("strava/authorize/", views.strava_authorize, name="strava-authorize"),
    path("strava/callback/", views.strava_callback, name="strava-callback"),
    path("strava/status/", views.strava_status, name="strava-status"),
    path("strava/atividades/", views.strava_atividades, name="strava-atividades"),
    path("google/contacts/connect/", google_contacts_connect, name="google_contacts_connect"),
    path("google/contacts/disconnect/", views.google_contacts_disconnect, name="google_contacts_disconnect"),
    path("google/contacts/callback/", google_contacts_callback, name="google_contacts_callback"),
    path("google/contacts/list/", views.google_contacts_list, name="google_contacts_list"),
    path("google/contacts/status/", GoogleContactsStatusView.as_view(), name="google-contacts-status"),
    
    # INSTAGRAM
    path("instagram/", InstagramFeedView.as_view(), name="instagram-feed"),
]
