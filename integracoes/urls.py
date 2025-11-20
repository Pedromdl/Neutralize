from django.urls import path
from . import views
from .views import InstagramFeedView

urlpatterns = [
    path("strava/authorize/", views.strava_authorize),  # 🔹 ADICIONE ESTA LINHA
    path("strava/callback/", views.strava_callback),
    path("strava/status/", views.strava_status),
    path("strava/atividades/", views.strava_atividades),
    path("instagram/", InstagramFeedView.as_view()),

]
