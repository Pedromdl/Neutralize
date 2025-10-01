from django.db import models

# Create your models here.

# Modelo de Evento
# Representa eventos como agendas, consultas

class EventoAgenda(models.Model):
    FREQUENCIA_CHOICES = [
        ("nenhuma", "Nenhuma"),
        ("diario", "Diário"),
        ("semanal", "Semanal"),
        ("mensal", "Mensal"),
    ]

    paciente = models.ForeignKey('api.Usuário', on_delete=models.CASCADE, null=True, blank=True, related_name='eventos_agenda')
    tipo = models.CharField(max_length=50)  # Ex: Consulta, Treino
    status = models.CharField(max_length=50)  # Ex: Confirmado, Realizado
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    responsavel = models.CharField(max_length=100)

    # Recorrência
    repetir = models.BooleanField(default=False)
    frequencia = models.CharField(max_length=20, choices=FREQUENCIA_CHOICES, default="nenhuma")
    repeticoes = models.PositiveIntegerField(blank=True, null=True)  # quantas vezes repetir

    evento_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='ocorrencias')

    def __str__(self):
        tipo = self.tipo if self.tipo else "Sem tipo"
        paciente = self.paciente.nome if self.paciente else "Sem paciente"
        data = self.data if self.data else "Sem data"
        return f"{tipo} - {paciente} ({data})"

