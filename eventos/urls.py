from rest_framework.routers import DefaultRouter
from .views import EventoAgendaViewSet

router = DefaultRouter()
router.register(r'eventosagenda', EventoAgendaViewSet)  # <-- usar nome único

urlpatterns = router.urls
