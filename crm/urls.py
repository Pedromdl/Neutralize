# crm/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import import_google_contacts, list_contacts, ContactViewSet, InteracaoViewSet, AcaoPlanejadaViewSet

router = DefaultRouter()
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"acoes-planejadas", AcaoPlanejadaViewSet, basename="acoes-planejadas")


interacao_list = InteracaoViewSet.as_view({
    "get": "list",
})

urlpatterns = [
    path("", include(router.urls)),
    path("contacts/import/google/", import_google_contacts, name="import_google_contacts"),
    path("contacts/list",list_contacts,name="list_contacts"),
    path("contacts/<int:pessoa_id>/interacoes/", interacao_list, name="contact-interacoes"),
]
