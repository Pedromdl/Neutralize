from django.db import models

# Create your models here.
class LancamentoFinanceiro(models.Model):
    STATUS_PAGAMENTO_CHOICES = [
        ("pendente", "Pendente"),
        ("recebido", "Recebido"),
    ]

    STATUS_NF_CHOICES = [
        ("nao_emitida", "Não Emitida"),
        ("emitida", "Emitida"),
    ]

    evento = models.OneToOneField('eventos.EventoAgenda', on_delete=models.CASCADE, related_name='lancamento')
    paciente = models.ForeignKey('api.Usuário', on_delete=models.CASCADE, related_name='lancamentos')
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tipo_servico = models.CharField(max_length=100, default="Consulta")
    status_pagamento = models.CharField(max_length=20, choices=STATUS_PAGAMENTO_CHOICES, default="pendente")
    status_nf = models.CharField(max_length=20, choices=STATUS_NF_CHOICES, default="nao_emitida")
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paciente.nome} - {self.evento.data} - {self.tipo_servico}"
    