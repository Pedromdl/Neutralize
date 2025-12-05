from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings
from encrypted_model_fields.fields import EncryptedTextField
import json
import hashlib
from datetime import timedelta
from django.utils import timezone

class Consentimento(models.Model):
    """
    Registra consentimento LGPD para ações específicas.
    Art. 7, inciso I da LGPD: consentimento livre, informado e revogável.
    """
    TIPO_CONSENTIMENTO_CHOICES = [
        ('DADOS_PESSOAIS', 'Coleta de Dados Pessoais'),
        ('DADOS_SAUDE', 'Coleta de Dados de Saúde'),
        ('MARKETING', 'Comunicações de Marketing'),
        ('COOKIES', 'Cookies e Rastreamento'),
        ('EXPORT_DADOS', 'Export de Dados Pessoais'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consentimentos_lgpd'
    )
    tipo = models.CharField(max_length=50, choices=TIPO_CONSENTIMENTO_CHOICES)
    descricao = models.TextField(help_text="Descrição clara do consentimento")
    consentido = models.BooleanField(default=False)
    data_consentimento = models.DateTimeField(auto_now_add=True)
    data_revogacao = models.DateTimeField(null=True, blank=True)
    ip_consentimento = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-data_consentimento']
        verbose_name_plural = 'Consentimentos'
        indexes = [
            models.Index(fields=['usuario', 'tipo']),
            models.Index(fields=['data_consentimento']),
        ]

    def __str__(self):
        status = "✅ Consentido" if self.consentido else "❌ Negado"
        return f"{self.usuario} - {self.get_tipo_display()} - {status}"

    def revogar(self):
        """Revoga consentimento (LGPD Art. 8)"""
        self.consentido = False
        self.data_revogacao = timezone.now()
        self.save()


class AuditLog(models.Model):
    """
    Log de auditoria LGPD-compliant.
    Registra TODAS as ações: CREATE, READ, UPDATE, DELETE, LOGIN, EXPORT.
    
    Art. 5, XII da LGPD: rastreabilidade de acesso a dados pessoais.
    """
    ACAO_CHOICES = [
        ('CREATE', '🆕 Criação'),
        ('READ', '👁️ Leitura'),
        ('UPDATE', '✏️ Atualização'),
        ('DELETE', '🗑️ Exclusão'),
        ('LOGIN', '🔐 Login'),
        ('LOGOUT', '🚪 Logout'),
        ('EXPORT', '📥 Export de Dados'),
        ('IMPORT', '📤 Import de Dados'),
        ('PERMISSAO_NEGADA', '❌ Acesso Negado'),
    ]

    DADOS_SENSIVEL_TIPOS = [
        ('CPF', 'CPF'),
        ('SAUDE', 'Dados de Saúde'),
        ('FINANCEIRO', 'Dados Financeiros'),
        ('LOCALIZACAO', 'Localização'),
        ('BIOMETRIA', 'Biometria'),
    ]

    # Usuário que realizou a ação
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_auditoria'
    )

    # O quê foi feito
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES)
    modelo = models.CharField(max_length=100)  # 'api.Usuario', 'accounts.CustomUser'
    objeto_id = models.CharField(max_length=100)  # ID do objeto afetado

    # Dados antes/depois (criptografado)
    dados_antes = EncryptedTextField(null=True, blank=True)
    dados_depois = EncryptedTextField(null=True, blank=True)

    # Contexto
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # LGPD: Consentimento
    consentimento = models.ForeignKey(
        Consentimento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )

    # LGPD: Dados sensíveis
    contem_dado_sensivel = models.CharField(
        max_length=20,
        choices=DADOS_SENSIVEL_TIPOS,
        null=True,
        blank=True
    )

    # LGPD: Retenção de dados (quando deletar conforme política)
    data_retencao = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data até quando o log será mantido (LGPD Art. 16)"
    )
    removido = models.BooleanField(default=False, help_text="Log anonimizado/removido (direito ao esquecimento)")

    # Hash para garantir integridade (audit trail imutável)
    hash_integridade = models.CharField(max_length=64)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Logs de Auditoria'
        indexes = [
            models.Index(fields=['usuario', 'timestamp']),
            models.Index(fields=['modelo', 'objeto_id']),
            models.Index(fields=['acao', 'timestamp']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['data_retencao']),
        ]

    def __str__(self):
        return f"{self.get_acao_display()} - {self.modelo} ({self.objeto_id}) - {self.usuario} - {self.timestamp.strftime('%d/%m/%Y %H:%M:%S')}"

    def calcular_hash_integridade(self):
        """Calcula hash SHA256 para garantir imutabilidade do log"""
        dados = f"{self.usuario_id}{self.acao}{self.modelo}{self.objeto_id}{self.timestamp}{self.dados_antes}{self.dados_depois}"
        return hashlib.sha256(dados.encode()).hexdigest()

    def save(self, *args, **kwargs):
        """Calcula hash antes de salvar"""
        if not self.hash_integridade:
            self.hash_integridade = self.calcular_hash_integridade()
        
        # Define retenção padrão (conforme LGPD)
        if not self.data_retencao:
            if self.acao in ['LOGIN', 'LOGOUT']:
                # Logs de acesso: 6 meses
                self.data_retencao = timezone.now() + timedelta(days=180)
            elif self.acao == 'DELETE':
                # Logs de exclusão: 2 anos (Art. 16)
                self.data_retencao = timezone.now() + timedelta(days=730)
            elif self.contem_dado_sensivel:
                # Dados sensíveis: 1 ano (mais rigoroso)
                self.data_retencao = timezone.now() + timedelta(days=365)
            else:
                # Outros: 30 dias
                self.data_retencao = timezone.now() + timedelta(days=30)
        
        super().save(*args, **kwargs)

    def anonimizar(self):
        """
        Implementa direito ao esquecimento (LGPD Art. 17).
        Remove dados sensíveis, mantém registro de que houve acesso.
        """
        self.usuario = None
        self.ip_address = None
        self.user_agent = None
        self.dados_antes = "[ANONIMIZADO - LGPD ART. 17]"
        self.dados_depois = "[ANONIMIZADO - LGPD ART. 17]"
        self.removido = True
        self.save()


class PolíticaRetencaoDados(models.Model):
    """
    Define políticas de retenção de dados para LGPD compliance.
    Art. 15, inciso I: "conservação em formato que permita identificação"
    """
    tipo_acao = models.CharField(max_length=20, choices=AuditLog.ACAO_CHOICES, unique=True)
    dias_retencao = models.IntegerField(help_text="Número de dias para manter o log")
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Política de Retenção'
        verbose_name_plural = 'Políticas de Retenção'

    def __str__(self):
        return f"{self.get_tipo_acao_display()} - {self.dias_retencao} dias"


class RelatorioAcessoDados(models.Model):
    """
    Relatório de "Quem acessou meus dados" - LGPD Art. 18
    Gerado sob demanda para atender direito de acesso do titular.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='relatorios_acesso'
    )
    data_geracao = models.DateTimeField(auto_now_add=True)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    acessos_registrados = models.IntegerField()
    hash_integridade = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ['-data_geracao']
        indexes = [
            models.Index(fields=['usuario', 'data_geracao']),
        ]

    def __str__(self):
        return f"Relatório de {self.usuario} - {self.data_geracao.strftime('%d/%m/%Y')}"
