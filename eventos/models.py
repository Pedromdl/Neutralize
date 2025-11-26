from django.db import models

# Create your models here.

# Modelo de Evento
# Representa eventos como agendas, consultas

class EventoAgenda(models.Model):
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

    def __str__(self):
        return f"{self.tipo or 'Sem tipo'} - {getattr(self.paciente,'nome','Sem paciente')} ({self.data or 'Sem data'})"

