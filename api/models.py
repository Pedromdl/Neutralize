from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.
class Usuário(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    endereço = models.CharField(max_length=255, blank=True, null=True)
    data_de_nascimento = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.nome

class Mobilidade(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='mobilidades')
    nome = models.CharField(max_length=100, verbose_name="Mobilidade")  # Campo obrigatório
    data_avaliacao = models.DateField(verbose_name="Data")
    lado_esquerdo = models.CharField(max_length=100, verbose_name="Lado Esquerdo")
    lado_direito = models.CharField(max_length=100, verbose_name="Lado Direito")
    observacao = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        ordering = ['-data_avaliacao']

    def __str__(self):
        return f"{self.nome} - {self.data_avaliacao}"
    
class ForcaMuscular(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='dadosdeforcamuscular')
    musculatura = models.CharField(max_length=100, verbose_name="Musculatura")
    data_avaliacao = models.DateField(verbose_name="Data")
    lado_esquerdo = models.CharField(max_length=100, verbose_name="Lado Esquerdo")
    lado_direito = models.CharField(max_length=100, verbose_name="Lado Direito")
    observacao = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
            verbose_name = "Força Muscular"
            verbose_name_plural = "Forças Musculares"
            ordering = ['-data_avaliacao']
            
    def __str__(self):
        return f"{self.paciente} - {self.data_avaliacao} - {self.musculatura}"
    
class CategoriaTeste(models.Model):
    """Tabela que contém todos os testes disponíveis"""
    nome = models.CharField(max_length=100, unique=True)

    class Meta:
            verbose_name = "Categoria de Teste"

    def __str__(self):  
        return self.nome

class TodosTestes(models.Model):
    """Tabela que contém todos os testes disponíveis"""
    nome = models.CharField(max_length=100, unique=True)
    categoria = models.ForeignKey(CategoriaTeste, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
            verbose_name = "Todos os Teste"

    def __str__(self):
        return f"{self.nome} ({self.categoria.nome if self.categoria else 'Sem categoria'})"

class TesteFuncao(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='dadosdetestes')
    teste = models.ForeignKey(TodosTestes, on_delete=models.CASCADE)  # Agora os testes são pré-definidos
    data_avaliacao = models.DateField(verbose_name="Data")
    lado_esquerdo = models.CharField(max_length=100, verbose_name="Lado Esquerdo")
    lado_direito = models.CharField(max_length=100, verbose_name="Lado Direito")
    observacao = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Teste de Função"
        verbose_name_plural = "Testes de Função"
        ordering = ['-data_avaliacao']

    def __str__(self):
        return f"{self.paciente} - {self.data_avaliacao} - {self.teste}"
    
class TesteDor(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='dadosdeteste_dor')
    teste = models.ForeignKey(TodosTestes, on_delete=models.CASCADE)  # Agora os testes são pré-definidos
    data_avaliacao = models.DateField(verbose_name="Data")
    resultado = models.CharField(max_length=100, verbose_name="Resultado")
    observacao = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Teste de Dor"
        verbose_name_plural = "Testes de Dor"
        ordering = ['-data_avaliacao']

    def __str__(self):
        return f"{self.paciente} - {self.data_avaliacao} - {self.teste} - {self.observacao}"
    
class PreAvaliacao(models.Model):
    titulo = models.CharField(max_length=200)
    texto = models.TextField()

    def __str__(self):
        return self.titulo

class Anamnese(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE)  # relacionamento com paciente
    conteudo_html = models.TextField()  # para salvar o HTML da avaliação
    data_avaliacao = models.DateField(verbose_name="Data")

    def __str__(self):
        return f"Avaliação do paciente {self.paciente.nome} em {self.data_avaliacao}"

class Pasta(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE)  # relacionamento com paciente
    nome = models.CharField(max_length=255)
    
class Secao(models.Model):
    pasta = models.ForeignKey(Pasta, on_delete=models.CASCADE, related_name='secoes')
    titulo = models.CharField(max_length=255)

class Orientacao(models.Model):
    secao = models.ForeignKey(Secao, on_delete=models.CASCADE, related_name='orientacoes')
    titulo = models.CharField(max_length=255)
    series = models.CharField(max_length=50)
    repeticoes = models.CharField(max_length=50)
    descricao = models.TextField(blank=True)
    video_url = models.URLField()

class Evento(models.Model):
    FREQUENCIA_CHOICES = [
        ("nenhuma", "Nenhuma"),
        ("diario", "Diário"),
        ("semanal", "Semanal"),
        ("mensal", "Mensal"),
    ]

    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, null=True, blank=True, related_name='eventos')
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
        return f"{self.tipo} - {self.paciente.nome} ({self.data})"

class Sessao(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='sessoes')
    data = models.DateField()
    titulo = models.CharField(blank=True, null=True, max_length=255)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f'{self.paciente} - {self.titulo} ({self.data})'
