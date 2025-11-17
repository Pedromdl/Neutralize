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