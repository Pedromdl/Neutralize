from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class Clinica(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, unique=True, null=True, blank=True)
    logo = models.ImageField(upload_to="clinicas/logos/", null=True, blank=True)
    endereco = models.CharField(max_length=255, blank=True)
    numero = models.CharField(max_length=255, blank=True)
    complemento = models.CharField(max_length=255, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

    @property
    def assinatura_ativa(self):
        """Retorna a assinatura ativa da clínica"""
        try:
            return self.assinatura_pagamento
        except Assinatura.DoesNotExist:
            return None

    def pode_adicionar_paciente(self):
        """Verifica se a clínica pode adicionar mais pacientes"""
        if not self.assinatura_ativa:
            return False
        
        assinatura = self.assinatura_ativa
        if assinatura.em_trial:
            return True
            
        return self.pacientes_cadastrados < assinatura.plano.max_pacientes

    @property
    def pacientes_cadastrados(self):
        """Retorna o número de pacientes cadastrados"""
        # Você precisará implementar essa lógica baseada no seu modelo de pacientes
        return 0  # Placeholder
    
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O usuário precisa ter um e-mail")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Administrador da Clínica'),
        ('profissional', 'Profissional'),
        ('paciente', 'Paciente'),
    ]
    clinica = models.ForeignKey('Clinica', on_delete=models.CASCADE, null=True, blank=True, related_name='usuarios')
    photo_google = models.URLField(blank=True, null=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    cpf = models.CharField(max_length=11, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='paciente'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def get_full_name(self):
        """Retorna o nome completo do usuário"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split('@')[0]  # Fallback para parte do email
    
    def get_short_name(self):
        """Retorna o primeiro nome"""
        return self.first_name if self.first_name else self.email.split('@')[0]

    def __str__(self):
        return self.email
    
from django.conf import settings
from django.utils import timezone

class DocumentoLegal(models.Model):
    TIPO_CHOICES = [
        ('termo_uso', 'Termo de Uso'),
        ('politica_privacidade', 'Política de Privacidade'),
        ('consentimento', 'Consentimento'),
    ]
    PUBLICO_CHOICES = [
        ('clinica', 'Clínica'),
        ('profissional', 'Profissional'),
        ('paciente', 'Paciente'),
        ('geral', 'Todos')
    ]

    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=150)
    conteudo = models.TextField()
    versao = models.CharField(max_length=10)
    publico = models.CharField(max_length=20, choices=PUBLICO_CHOICES, default='geral')
    data_publicacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-data_publicacao']  # sempre o mais recente primeiro

    def __str__(self):
        return f"{self.titulo} v{self.versao} ({self.get_tipo_display()})"
    
class AceiteDocumento(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    documento = models.ForeignKey(DocumentoLegal, on_delete=models.CASCADE)
    data_aceite = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('usuario', 'documento')  # evita múltiplos registros do mesmo documento

    def __str__(self):
        return f"{self.usuario.email} aceitou {self.documento.titulo} v{self.documento.versao}"
    
class Plano(models.Model):
    """
    Define os planos disponíveis para comercialização
    """
    TIPOS_PLANO = [
        ('starter', 'Starter - Autônomos'),
        ('professional', 'Professional - Clínicas'), 
        ('clinic', 'Clinic - Redes'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS_PLANO, unique=True)
    preco_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(blank=True)
    
    # Limites
    max_pacientes = models.IntegerField()
    max_usuarios = models.IntegerField()
    max_avaliacoes_mes = models.IntegerField(null=True, blank=True)  # ou ilimitado
    
    # Recursos
    recursos = models.JSONField(default=dict, help_text="Recursos disponíveis no plano")
    
    # Trial
    dias_trial = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Plano"
        verbose_name_plural = "Planos"
    
    def __str__(self):
        return f"{self.nome} - R$ {self.preco_mensal}/mês"

class Assinatura(models.Model):
    """
    Controla a assinatura de cada clínica
    """
    STATUS_CHOICES = [
        ('trial', 'Período de Trial'),
        ('ativa', 'Ativa'),
        ('suspensa', 'Suspensa'),
        ('cancelada', 'Cancelada'),
    ]
    
    clinica = models.OneToOneField(Clinica, on_delete=models.CASCADE, related_name='assinatura')
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT)
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim_trial = models.DateTimeField(null=True, blank=True)
    data_proximo_pagamento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    
    # Controle de uso
    pacientes_cadastrados = models.IntegerField(default=0)
    avaliacoes_mes = models.IntegerField(default=0)
    ultimo_reset_uso = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"
    
    def __str__(self):
        return f"{self.clinica.nome} - {self.plano.nome}"
    
    @property
    def em_trial(self):
        if self.data_fim_trial:
            return timezone.now() < self.data_fim_trial
        return False
    
    @property
    def atingiu_limite_pacientes(self):
        return self.pacientes_cadastrados >= self.plano.max_pacientes