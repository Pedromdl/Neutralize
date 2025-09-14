from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PastaViewSet,
    SecaoViewSet,
    BancodeExercicioViewSet,
    TreinoViewSet,
    TreinoExecutadoViewSet,
    ExercicioPrescritoViewSet,
    resumo_treinos
)

# 🔹 Router para todos os ViewSets
router = DefaultRouter()
router.register(r'pastas', PastaViewSet, basename='pasta')
router.register(r'secoes', SecaoViewSet, basename='secao')
router.register(r'bancoexercicios', BancodeExercicioViewSet, basename='bancoexercicio')
router.register(r'exerciciosprescritos', ExercicioPrescritoViewSet, basename='exercicioprescrito')
router.register(r'treinos', TreinoViewSet, basename='treino')
router.register(r'treinosexecutados', TreinoExecutadoViewSet, basename='treinoexecutado')

# 🔹 URLs finais
urlpatterns = [
    path('resumo_treinos/', resumo_treinos, name='resumo-treinos'),  # endpoint customizado
    path('', include(router.urls)),  # todas as rotas do router
]