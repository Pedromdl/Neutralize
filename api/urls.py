from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    UsuárioViewSet, ForcaMuscularViewSet, MobilidadeViewSet, TesteFuncaoViewSet, 
    TodosTestesViewSet, TesteDorViewSet, PreAvaliacaoViewSet, DatasDisponiveisAPIView, AnamneseViewSet, PastaViewSet, 
    SecaoViewSet, OrientacaoViewSet
)

router = DefaultRouter()
router.register(r'usuarios', UsuárioViewSet)
router.register(r'forca', ForcaMuscularViewSet)
router.register(r'mobilidade', MobilidadeViewSet)
router.register(r'testefuncao', TesteFuncaoViewSet)
router.register(r'testedor', TesteDorViewSet, basename='teste-dor')
router.register(r'testes', TodosTestesViewSet, basename='teste-funcao')
router.register(r'preavaliacao', PreAvaliacaoViewSet, basename='pre-avaliacao')
router.register(r'anamnese', AnamneseViewSet, basename='anamnese')
router.register(r'pastas', PastaViewSet)
router.register(r'secoes', SecaoViewSet)
router.register(r'orientacoes', OrientacaoViewSet)


urlpatterns = [

    path('datas-disponiveis/', DatasDisponiveisAPIView.as_view(), name='datas-disponiveis'),
]

from .views import exportar_avaliacao_docx

urlpatterns += [
    path('anamnese/<int:pk>/exportar-docx/', exportar_avaliacao_docx, name='exportar-docx'),
]



urlpatterns += router.urls
