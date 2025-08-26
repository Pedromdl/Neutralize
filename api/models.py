from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


# Create your models here.
# Modelos de Usuário
class Usuário(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True, blank=True, null=True)  # Formato: 000.000.000-00
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    endereço = models.CharField(max_length=255, blank=True, null=True)
    data_de_nascimento = models.DateField(blank=True, null=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="perfil_api")

    def __str__(self):
        return self.nome
    
# Modelos de Dados
    

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


class Mobilidade(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='mobilidades')
    nome = models.ForeignKey(TodosTestes, on_delete=models.CASCADE, related_name='mobilidades', null=True, blank=True)  # Teste pré-definido
    data_avaliacao = models.DateField(verbose_name="Data")
    lado_esquerdo = models.CharField(max_length=100, verbose_name="Lado Esquerdo")
    lado_direito = models.CharField(max_length=100, verbose_name="Lado Direito")
    observacao = models.TextField(null=True, blank=True, verbose_name="Observações")

    class Meta:
        ordering = ['-data_avaliacao']

    def __str__(self):
        return f"{self.nome} - {self.data_avaliacao}"
    
class ForcaMuscular(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='dadosdeforcamuscular')
    movimento_forca = models.ForeignKey(TodosTestes, on_delete=models.CASCADE, related_name='forcas_musculares', null=True, blank=True, verbose_name="Movimento")  # Teste pré-definido
    data_avaliacao = models.DateField(verbose_name="Data")
    lado_esquerdo = models.CharField(max_length=100, verbose_name="Lado Esquerdo")
    lado_direito = models.CharField(max_length=100, verbose_name="Lado Direito")
    observacao = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
            verbose_name = "Força Muscular"
            verbose_name_plural = "Forças Musculares"
            ordering = ['-data_avaliacao']
            
    def __str__(self):
        return f"{self.paciente} - {self.data_avaliacao} - {self.movimento_forca}"
    
class Estabilidade(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='dadosdeestabilidade')
    movimento_estabilidade = models.ForeignKey(TodosTestes, on_delete=models.CASCADE, related_name='estabilidades', null=True, blank=True, verbose_name="Movimento")  # Teste pré-definido
    data_avaliacao = models.DateField(verbose_name="Data")
    lado_esquerdo = models.CharField(max_length=100, verbose_name="Lado Esquerdo")
    lado_direito = models.CharField(max_length=100, verbose_name="Lado Direito")
    resultado_unico = models.CharField(max_length=100, blank=True, null=True, verbose_name="Resultado")
    observacao = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
            verbose_name = "Estabilidade"
            verbose_name_plural = "Estabilidades"
            ordering = ['-data_avaliacao']
            
    def __str__(self):
        nome_teste = self.movimento_estabilidade.nome if self.movimento_estabilidade else "Sem teste"
        return f"{self.paciente} - {self.data_avaliacao} - {nome_teste}"

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
    
# Modelos de Avaliações e Históricos Clínicos

class PreAvaliacao(models.Model):
    titulo = models.CharField(max_length=200)
    texto = models.TextField()

    class Meta:
        verbose_name = "Pré-Avaliação"
        verbose_name_plural = "Pré-Avaliações"

    def __str__(self):
        return self.titulo



class Anamnese(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE)  # relacionamento com paciente
    conteudo_html = models.TextField()  # para salvar o HTML da avaliação
    data_avaliacao = models.DateField(verbose_name="Data")

    def __str__(self):
        return f"Avaliação do paciente {self.paciente.nome} em {self.data_avaliacao}"

# Modelo de Evento
# Representa eventos como agendas, consultas

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
        tipo = self.tipo if self.tipo else "Sem tipo"
        paciente = self.paciente.nome if self.paciente else "Sem paciente"
        data = self.data if self.data else "Sem data"
        return f"{tipo} - {paciente} ({data})"


# Modelo de Registros de Sessão

class Sessao(models.Model):
    paciente = models.ForeignKey(Usuário, on_delete=models.CASCADE, related_name='sessoes')
    data = models.DateField()
    titulo = models.CharField(blank=True, null=True, max_length=255)
    descricao = models.TextField(blank=True)

    class Meta:
        verbose_name = "Sessão"
        verbose_name_plural = "Sessões"

    def __str__(self):
        return f'{self.paciente} - {self.titulo} ({self.data})'
