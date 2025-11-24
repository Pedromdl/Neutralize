from django.urls import path
from . import views

app_name = 'pagamentos'

urlpatterns = [
    path('planos/', views.listar_planos, name='listar_planos'),
    path('assinatura/', views.detalhes_assinatura, name='minha_assinatura'),  # Sem ID
    path('assinatura/<int:assinatura_id>/', views.detalhes_assinatura, name='detalhes_assinatura'),
    path('assinatura/<int:assinatura_id>/cancelar/', views.cancelar_assinatura, name='cancelar_assinatura'),
    path('webhook/asaas/', views.webhook_asaas, name='webhook_asaas'),
]