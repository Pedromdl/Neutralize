from rest_framework import serializers
from .models import LancamentoFinanceiro


class LancamentoFinanceiroSerializer(serializers.ModelSerializer):
    paciente_nome = serializers.CharField(source="paciente.nome", read_only=True)
    data_evento = serializers.DateField(source="evento.data", read_only=True)
    responsavel_evento = serializers.CharField(source="evento.responsavel", read_only=True)  # <-- aqui

    class Meta:
        model = LancamentoFinanceiro
        fields = [
            "id", "paciente_nome", "data_evento", "valor", "tipo_servico",
            "status_pagamento", "status_nf", "responsavel_evento"
        ]
