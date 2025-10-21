from django.contrib import admin
from .models import LancamentoFinanceiro, BancodeAtendimento, TransacaoFinanceira, TransacaoOperacional

# Register your models here.
admin.site.register(LancamentoFinanceiro)

@admin.register(BancodeAtendimento)
class BancodeAtendimentoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'saldo_atual', 'data_atualizacao')
    search_fields = ('paciente__nome',)

@admin.register(TransacaoFinanceira)
class TransacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('banco', 'tipo', 'num_atendimentos', 'valor_total', 'descricao', 'data', 'status_pagamento')
    list_filter = ('data', 'status_pagamento')
    search_fields = ('banco__paciente__nome', 'descricao')

@admin.register(TransacaoOperacional)
class TransacaoOperacionalAdmin(admin.ModelAdmin):
    list_display = ('banco', 'tipo', 'data', 'num_atendimentos', 'descricao')
    search_fields = ('banco__paciente__nome', 'descricao')
