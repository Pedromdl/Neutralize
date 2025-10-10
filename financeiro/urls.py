from rest_framework.routers import DefaultRouter
from .views import LancamentoFinanceiroViewSet

router = DefaultRouter()
router.register(r"financeiro", LancamentoFinanceiroViewSet, basename="financeiro")

urlpatterns = router.urls