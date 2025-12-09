from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    OrganizacaoDetailView, UserProfileView, UserListView, GoogleAuthView, LoginView,
    DocumentoLegalListView, RegistrarAceiteDocumentoView,
    RegisterAdminClinicaView, CustomUserViewSet, RegisterPacienteView, 
)

router = DefaultRouter()
router.register(r'customuser', CustomUserViewSet, basename='customuser')

urlpatterns = [
    path('', include(router.urls)),  # <-- IMPORTANTE

    path('minha-organizacao/', OrganizacaoDetailView.as_view(), name='minha-organizacao'),
    path('registro/', RegisterPacienteView.as_view(), name='registro-paciente'),  # <-- NOVA URL AQUI
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('google/', GoogleAuthView.as_view(), name='google-auth'),
    path('login/', LoginView.as_view(), name='login-trad'),
    path('registrar-clinica/', RegisterAdminClinicaView.as_view(), name='registro-clinica'),
    path('documentos/', DocumentoLegalListView.as_view(), name='documentos-list'),
    path('documentos/aceitar/', RegistrarAceiteDocumentoView.as_view(), name='documentos-aceitar'),
]

