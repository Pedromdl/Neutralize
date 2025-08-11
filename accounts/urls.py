from django.urls import path
from .views import UserProfileView, UserListView, GoogleAuthView

urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('users/', UserListView.as_view(), name='user-list'),
    path("google/", GoogleAuthView.as_view(), name="google-auth"),

]
