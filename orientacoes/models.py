from django.db import models


# ---------------------------
# Estrutura de pasta e seção
# ---------------------------

class Pasta(models.Model):
    paciente = models.ForeignKey('api.Usuário', on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    
    def __str__(self):
        return self.nome


class Secao(models.Model):
    pasta = models.ForeignKey(Pasta, on_delete=models.CASCADE, related_name='secoes')
    titulo = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Seção"
        verbose_name_plural = "Seções"

    def __str__(self):
        return self.titulo


# ---------------------------
# Orientações (exercícios)
# ---------------------------

class BancodeExercicio(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name = "Banco de Exercício"
        verbose_name_plural = "Bancos de Exercício"

    def __str__(self):
        return self.titulo


# ---------------------------
# Treino como template
# ---------------------------

class Treino(models.Model):
    """Treino planejado, associado à seção"""
    secao = models.ForeignKey("Secao", on_delete=models.CASCADE, related_name="treinos")
    nome = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Treino"
        verbose_name_plural = "Treinos"

    def __str__(self):
        return f"{self.nome} ({self.secao})"


class ExercicioPrescrito(models.Model):
    """Exercício planejado dentro de um treino (template)"""
    treino = models.ForeignKey(Treino, on_delete=models.CASCADE, related_name="exercicios")
    orientacao = models.ForeignKey(BancodeExercicio, on_delete=models.CASCADE)
    series_planejadas = models.PositiveIntegerField(default=1)
    repeticoes_planejadas = models.PositiveIntegerField(default=0)
    carga_planejada = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.orientacao.titulo} - {self.treino}"


# ---------------------------
# Execução do treino
# ---------------------------

class TreinoExecutado(models.Model):
    """Registro de cada vez que o paciente realiza o treino"""
    treino = models.ForeignKey(Treino, on_delete=models.CASCADE, related_name="execucoes")
    paciente = models.ForeignKey("api.Usuário", on_delete=models.CASCADE)
    data = models.DateTimeField(auto_now_add=True)
    tempo_total = models.PositiveIntegerField(default=0)
    finalizado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.treino.nome} - {self.paciente} - {self.data.date()}"
    
class ExercicioExecutado(models.Model):
    treino_executado = models.ForeignKey(TreinoExecutado, on_delete=models.CASCADE, related_name="exercicios")
    exercicio = models.ForeignKey(ExercicioPrescrito, on_delete=models.CASCADE)
    rpe = models.IntegerField(null=True, blank=True)

class SerieRealizada(models.Model):
    """Séries executadas em uma execução de treino"""
    execucao = models.ForeignKey(ExercicioExecutado, on_delete=models.CASCADE, related_name="series")
    exercicio = models.ForeignKey(ExercicioPrescrito, on_delete=models.CASCADE)
    numero = models.PositiveIntegerField(blank=True, null=True)
    repeticoes = models.PositiveIntegerField(blank=True, null=True)  # realizado
    carga = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # realizado

    def __str__(self):
        return f"Série {self.numero} - {self.exercicio.orientacao.titulo}"