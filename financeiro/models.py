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

class BancodeAtendimento(models.Model):
    paciente = models.OneToOneField('api.Usuário', on_delete=models.CASCADE, related_name='banco_atendimento')
    saldo_atual = models.IntegerField(default=0)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.paciente.nome} — Saldo: {self.saldo_atual}"

class TransacaoFinanceira(models.Model):
    STATUS_PAGAMENTO_CHOICES = (
        ('aprovado', 'Aprovado'),
        ('estornado', 'Estornado'),
        ('cancelado', 'Cancelado'),
    )
    TIPO_CHOICES = (
        ('debito', 'Débito'),
        ('credito', 'Crédito'),
    )

    paciente = models.ForeignKey('api.Usuário', on_delete=models.CASCADE)
    banco = models.ForeignKey('BancodeAtendimento', on_delete=models.CASCADE, blank=True, null=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    num_atendimentos = models.PositiveIntegerField(default=0)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descricao = models.CharField(max_length=255, blank=True, null=True)
    status_pagamento = models.CharField(max_length=20, choices=STATUS_PAGAMENTO_CHOICES, default='pendente')
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pagamento {self.id} — {self.paciente.nome} ({self.status_pagamento})"
    
class TransacaoOperacional(models.Model):
    TIPO_CHOICES = (
        ('debito', 'Débito'),
        ('credito', 'Crédito'),
    )

    paciente = models.ForeignKey('api.Usuário', on_delete=models.CASCADE)
    banco = models.ForeignKey('BancodeAtendimento', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    evento = models.OneToOneField('eventos.EventoAgenda', on_delete=models.CASCADE, null=True, blank=True)
    num_atendimentos = models.PositiveIntegerField(default=1)
    descricao = models.CharField(max_length=255, blank=True, null=True)
    data = models.DateTimeField(auto_now_add=True)
    is_reversao = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.paciente.nome} ({self.descricao})"
