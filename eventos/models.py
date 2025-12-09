from django.db import models

# Create your models here.

# Modelo de Evento
# Representa eventos como agendas, consultas

from django.db import models
from django.contrib.postgres.fields import ArrayField  # se você estiver usando PostgreSQL

class EventoAgenda(models.Model):
    # ---- SEUS CAMPOS ATUAIS (não vamos alterar nada) ----
    organizacao = models.ForeignKey('accounts.Organizacao', on_delete=models.CASCADE, null=True, blank=True, related_name='eventos_agenda')
    paciente = models.ForeignKey('api.Usuário', on_delete=models.CASCADE, null=True, blank=True, related_name='eventos_paciente')
    tipo = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[("pendente","Pendente"), ("confirmado","Confirmado"), ("realizado","Realizado"), ("cancelado","Cancelado")],
        default="pendente"
    )
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    responsavel = models.CharField(max_length=100)

    repetir = models.BooleanField(default=False)
    frequencia = models.CharField(
        max_length=20,
        choices=[("nenhuma","Nenhuma"), ("diario","Diário"), ("semanal","Semanal"), ("mensal","Mensal")],
        default="nenhuma"
    )
    repeticoes = models.PositiveIntegerField(blank=True, null=True)

    evento_pai = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='ocorrencias')

    # ---- NOVOS CAMPOS (Passo 1) ----

    # Armazena regras complexas de repetição
    rrule = models.TextField(null=True, blank=True)

    # Lista de datas que devem ser excluídas (EXDATE)
    exdates = ArrayField(
        base_field=models.DateField(),
        null=True,
        blank=True,
        default=list
    )

    def __str__(self):
        return f"{self.tipo or 'Sem tipo'} - {getattr(self.paciente,'nome','Sem paciente')} ({self.data or 'Sem data'})"

class EventoExcecao(models.Model):
    evento_pai = models.ForeignKey(EventoAgenda, on_delete=models.CASCADE, related_name="excecoes")

    # A data original da instância que foi modificada
    recurrence_id = models.DateField()

    # Os dados sobrescritos
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    tipo = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("pendente","Pendente"), ("confirmado","Confirmado"), ("realizado","Realizado"), ("cancelado","Cancelado")],
        null=True,
        blank=True
    )
    responsavel = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Exceção para {self.evento_pai_id} em {self.recurrence_id}"



