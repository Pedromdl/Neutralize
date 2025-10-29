from django.db import models

# Create your models here.

class EstadoIA(models.Model):
    numero = models.CharField(max_length=20, unique=True)
    ia_ativa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.numero} - {'Ativa' if self.ia_ativa else 'Desativada'}"


class Mensagem(models.Model):
    numero = models.CharField(max_length=20)
    texto = models.TextField()
    resposta = models.TextField()
    data = models.DateTimeField(auto_now_add=True)
    ia_ativa = models.BooleanField(default=True)  # 🔥 novo campo

