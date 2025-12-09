from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class ProvedorPagamento(models.Model):
    """
    Configuração dos provedores de pagamento
    """
    nome = models.CharField(max_length=100)
    tipo = models.CharField(
        max_length=20,
        choices=[('asaas', 'ASAAS'), ('stripe', 'Stripe'), ('mercadopago', 'Mercado Pago')],
        default='asaas'
    )
    api_key = models.CharField(max_length=255)
    base_url = models.URLField()
    webhook_token = models.CharField(max_length=255, blank=True)
    sandbox = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Provedor de Pagamento"
        verbose_name_plural = "Provedores de Pagamento"
    
    def __str__(self):
        return f"{self.nome} ({'Sandbox' if self.sandbox else 'Produção'})"

class PlanoPagamento(models.Model):
    """
    Planos disponíveis para assinatura
    """
    TIPOS_PLANO = [
        ('starter', 'Starter - Autônomos'),
        ('professional', 'Professional - Clínicas'), 
        ('clinic', 'Clinic - Redes'),
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS_PLANO, unique=True)
    preco_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(blank=True)
    
    # ID externo no provedor
    id_externo = models.CharField(max_length=100, blank=True, null=True)
    
    # Limites
    max_pacientes = models.IntegerField()
    max_usuarios = models.IntegerField()
    max_avaliacoes_mes = models.IntegerField(null=True, blank=True)
    
    # Recursos
    recursos = models.JSONField(default=dict, help_text="Recursos disponíveis no plano")
    
    # Trial
    dias_trial = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Plano de Pagamento"
        verbose_name_plural = "Planos de Pagamento"
    
    def __str__(self):
        return f"{self.nome} - R$ {self.preco_mensal}/mês"


class Assinatura(models.Model):
    """
    Assinaturas das clínicas
    """
    STATUS_CHOICES = [
        ('trial', 'Período de Trial'),
        ('ativa', 'Ativa'),
        ('suspensa', 'Suspensa'),
        ('cancelada', 'Cancelada'),
        ('aguardando_pagamento', 'Aguardando Pagamento'),
        ('expirada', 'Expirada'),  # ← ADICIONE ESTA LINHA
    ]
    
    METODO_PAGAMENTO_CHOICES = [
        ('credit_card', 'Cartão de Crédito'), 
        ('boleto', 'Boleto'), 
        ('pix', 'PIX')
    ]
    
    organizacao = models.ForeignKey('accounts.Organizacao', on_delete=models.CASCADE, related_name='assinatura_pagamento', null=True, blank= True,)
    plano = models.ForeignKey('PlanoPagamento', on_delete=models.PROTECT)
    provedor = models.ForeignKey('ProvedorPagamento', on_delete=models.PROTECT)
    
    # IDs externos
    id_cliente_externo = models.CharField(max_length=100, blank=True, null=True)
    id_assinatura_externo = models.CharField(max_length=100, blank=True, null=True)
    
    # Datas
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_fim_trial = models.DateTimeField(null=True, blank=True)
    data_proximo_pagamento = models.DateTimeField(null=True, blank=True)
    data_cancelamento = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    
    # Método de pagamento
    metodo_pagamento = models.CharField(
        max_length=20, 
        choices=METODO_PAGAMENTO_CHOICES,  # ← Usar a constante definida acima
        blank=True, null=True
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"
    
    def __str__(self):
        return f"{self.organizacao.nome} - {self.plano.nome}"
    
    @property
    def em_trial(self):
        """Verifica se está no período de trial"""
        if self.data_fim_trial:
            return timezone.now() < self.data_fim_trial
        return False
    
    @property
    def precisa_pagamento(self):
        hoje = timezone.now().date()

        # Se está cancelada, mas ainda dentro do período já pago → acesso liberado
        if self.status == "cancelada" and hoje <= self.data_proximo_pagamento:
            return False

        # Trial expirado
        if self.status == "trial" and not self.em_trial:
            return True

        # Status realmente bloqueantes
        return self.status in ["aguardando_pagamento", "expirada"]

    
    def expirar_trial(self):
        """Muda status para aguardando pagamento quando trial expira"""
        if self.status == 'trial' and not self.em_trial:
            self.status = 'aguardando_pagamento'
            self.save()
            return True
        return False
    
    def atualizar_expiracao(self):
        """Atualiza automaticamente o status da assinatura conforme as datas."""
        hoje = timezone.now().date()

        # 1️⃣ Trial expira sozinho
        if self.status == "trial" and not self.em_trial:
            self.status = "aguardando_pagamento"
            self.save(update_fields=["status"])
            return

        # 2️⃣ Assinatura ativa → verificar se venceu
        if self.status == "ativa":
            if self.data_proximo_pagamento and hoje > self.data_proximo_pagamento:
                # Passou da data sem pagar → bloqueia
                self.status = "aguardando_pagamento"
                self.save(update_fields=["status"])
            return

        # 3️⃣ Assinatura cancelada → manter acesso até data_proximo_pagamento
        if self.status == "cancelada":
            if self.data_proximo_pagamento and hoje > self.data_proximo_pagamento:
                self.status = "expirada"
                self.save(update_fields=["status"])
            return

        # 4️⃣ Suspensa → se passar data limite → expira
        if self.status == "suspensa":
            if self.data_proximo_pagamento and hoje > self.data_proximo_pagamento:
                self.status = "expirada"
                self.save(update_fields=["status"])
            return

    
    def ativar_com_cartao(self, cartao_token, ultimos_digitos, bandeira):
        """Ativa assinatura com cartão após trial"""
        self.cartao_token = cartao_token
        self.ultimos_digitos = ultimos_digitos
        self.bandeira_cartao = bandeira
        self.status = 'ativa'
        self.metodo_pagamento = 'credit_card'
        self.data_proximo_pagamento = timezone.now() + timedelta(days=30)
        self.save()

class TransacaoPagamento(models.Model):
    """
    Registro de transações de pagamento
    """
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('confirmed', 'Confirmado'),
        ('received', 'Recebido'),
        ('overdue', 'Atrasado'),
        ('refunded', 'Estornado'),
        ('cancelled', 'Cancelado'),
    ]
    
    assinatura = models.ForeignKey(
        Assinatura, 
        on_delete=models.CASCADE, 
        related_name='transacoes'
    )
    id_transacao_externo = models.CharField(max_length=100, unique=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    metodo_pagamento = models.CharField(max_length=20, blank=True, null=True)
    
    # Links de pagamento
    url_boleto = models.URLField(blank=True, null=True)
    codigo_pix = models.TextField(blank=True, null=True)
    qrcode_pix = models.TextField(blank=True, null=True)
    
    # Dados da transação
    dados_transacao = models.JSONField(default=dict, blank=True)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Transação de Pagamento"
        verbose_name_plural = "Transações de Pagamento"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Transação {self.id_transacao_externo} - R$ {self.valor}"

class WebhookLog(models.Model):
    """
    Log de webhooks recebidos
    """
    provedor = models.ForeignKey(ProvedorPagamento, on_delete=models.CASCADE)
    payload = models.JSONField()
    evento = models.CharField(max_length=100)
    id_externo = models.CharField(max_length=100, blank=True)
    processado = models.BooleanField(default=False)
    erro = models.TextField(blank=True)
    
    data_recebimento = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log de Webhook"
        verbose_name_plural = "Logs de Webhook"
        ordering = ['-data_recebimento']
    
    def __str__(self):
        return f"Webhook {self.evento} - {self.data_recebimento}"