from rest_framework.routers import DefaultRouter
from django.urls import path


from .views import (
    UsuárioViewSet, ForcaMuscularViewSet, MobilidadeViewSet, EstabilidadeViewSet, TesteFuncaoViewSet,
    TodosTestesViewSet, TesteDorViewSet, PreAvaliacaoViewSet, DatasDisponiveisAPIView, AnamneseViewSet, 
    EventoViewSet, SessaoViewSet,
)

router = DefaultRouter()
router.register(r'usuarios', UsuárioViewSet)
router.register(r'forca', ForcaMuscularViewSet)
router.register(r'mobilidade', MobilidadeViewSet)
router.register(r'estabilidade', EstabilidadeViewSet)
router.register(r'testefuncao', TesteFuncaoViewSet)
router.register(r'testedor', TesteDorViewSet, basename='teste-dor')
router.register(r'testes', TodosTestesViewSet, basename='todos-testes')
router.register(r'preavaliacao', PreAvaliacaoViewSet, basename='pre-avaliacao')
router.register(r'anamnese', AnamneseViewSet, basename='anamnese')
router.register(r'eventos', EventoViewSet)
router.register(r'sessoes', SessaoViewSet, basename='sessao')


from .views import (exportar_avaliacao_docx, gerar_relatorio_pdf, visualizar_relatorio, relatorio_publico, forca_publica, datas_disponiveis_publicas, mobilidade_publica, estabilidade_publica,
                    funcao_publica, dor_publica, usuario_publico, gerar_relatorio)

urlpatterns = [

    path('datas-disponiveis/', DatasDisponiveisAPIView.as_view(), name='datas-disponiveis'),
    path('gerar-relatorio/<int:paciente_id>/', gerar_relatorio, name='gerar-relatorio'),
    path('relatorio-publico/<str:token>/', relatorio_publico, name='relatorio-publico'),
    path('forca-publica/<str:token>/', forca_publica, name='forca-publica'),
    path('mobilidade-publica/<str:token>/', mobilidade_publica, name='mobilidade_publica'),
    path('estabilidade-publica/<str:token>/', estabilidade_publica, name='estabilidade-publica'),
    path('funcao-publica/<str:token>/', funcao_publica, name='funcao-publica'),
    path('datas-publicas/<str:token>/', datas_disponiveis_publicas, name='datas_publicas'),
    path('dor-publica/<str:token>/', dor_publica, name='dor-publica'),
    path('usuario-publico/<str:token>/', usuario_publico, name='usuario-publico'),

]


urlpatterns += [
    path('anamnese/<int:pk>/exportar-docx/', exportar_avaliacao_docx, name='exportar-docx'),
    path("relatorio/<int:paciente_id>/pdf/", gerar_relatorio_pdf, name="gerar_relatorio_pdf"),
    path("relatorio/<int:paciente_id>/visualizar/", visualizar_relatorio, name="visualizar_relatorio"),


]

urlpatterns += router.urls
