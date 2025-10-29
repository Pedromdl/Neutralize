from django.urls import path
from .views import webhook, listar_mensagens, enviar_mensagem_manual, alternar_ia, estado_ia

urlpatterns = [
    path("webhook/", webhook, name="whatsapp_webhook"),
    path("mensagens/", listar_mensagens, name="listar_mensagens"),
    path("enviar-manual/", enviar_mensagem_manual),
    path("alternar-ia/", alternar_ia),
    path("estado-ia/", estado_ia),


]
