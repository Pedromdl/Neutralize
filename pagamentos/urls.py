from django.urls import path
from . import views

app_name = 'pagamentos'

urlpatterns = [
    path('planos/', views.listar_planos, name='listar_planos'),

    # Assinatura atual (sem ID)
    path('assinatura/', views.detalhes_assinatura, name='minha_assinatura'),

    # Detalhes de uma assinatura específica
    path('assinatura/<int:assinatura_id>/', views.detalhes_assinatura, name='detalhes_assinatura'),

    # Cancelar assinatura
    path('assinatura/<int:assinatura_id>/cancelar/', views.cancelar_assinatura, name='cancelar_assinatura'),

    # 🚀 NOVA ROTA: ativar assinatura com cartão (Asaas)
    path('assinatura/<int:assinatura_id>/ativar-com-cartao/', views.ativar_assinatura_com_cartao,name='ativar_assinatura_com_cartao'),
    path('assinatura/<int:assinatura_id>/ativar-usando-token/', views.ativar_assinatura_usando_token, name='ativar_assinatura_usando_token'),
    
    # Webhook Asaas
    path('webhook/asaas/', views.webhook_asaas, name='webhook_asaas'),
]
