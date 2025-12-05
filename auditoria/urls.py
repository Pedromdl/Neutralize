from django.urls import path, include
from rest_framework.routers import DefaultRouter
from auditoria.views import (
    ConsentimentoViewSet, AuditLogViewSet, RelatorioAcessoDadosViewSet,
    DireitoEsquecimentoViewSet, PolíticaRetencaoDadosViewSet
)

router = DefaultRouter()
router.register(r'consentimentos', ConsentimentoViewSet, basename='consentimento')
router.register(r'logs', AuditLogViewSet, basename='auditlog')
router.register(r'relatorios', RelatorioAcessoDadosViewSet, basename='relatorio')
router.register(r'direito-esquecimento', DireitoEsquecimentoViewSet, basename='esquecimento')
router.register(r'politicas-retencao', PolíticaRetencaoDadosViewSet, basename='politica')

urlpatterns = [
    path('', include(router.urls)),
]
