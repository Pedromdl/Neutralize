from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Suas APIs
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('api.urls')),

    # Autenticação padrão (dj-rest-auth)
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),

    # Login social Google (allauth)
    # path('auth/', include('allauth.urls')),
    path("api/auth/", include("accounts.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
