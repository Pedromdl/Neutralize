from django.contrib import admin
from .models import ProvedorPagamento, PlanoPagamento, Assinatura, TransacaoPagamento, WebhookLog

@admin.register(ProvedorPagamento)
class ProvedorPagamentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'sandbox', 'ativo']
    list_filter = ['tipo', 'sandbox', 'ativo']

@admin.register(PlanoPagamento)
class PlanoPagamentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'preco_mensal', 'dias_trial', 'ativo']
    list_filter = ['tipo', 'ativo']

@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ['id', 'organizacao', 'plano', 'status', 'data_inicio', 'data_proximo_pagamento']
    list_filter = ['status', 'plano', 'metodo_pagamento']
    search_fields = ['organizacao__nome']

@admin.register(TransacaoPagamento)
class TransacaoPagamentoAdmin(admin.ModelAdmin):
    list_display = ['id_transacao_externo', 'assinatura', 'valor', 'status', 'data_vencimento']
    list_filter = ['status', 'metodo_pagamento']
    search_fields = ['id_transacao_externo', 'assinatura__organizacao__nome']

@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['provedor', 'evento', 'processado', 'data_recebimento']
    list_filter = ['provedor', 'evento', 'processado']
    readonly_fields = ['data_recebimento']