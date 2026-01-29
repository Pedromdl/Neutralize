from django.db import models


class Contact(models.Model):
    user = models.ForeignKey(
        "accounts.CustomUser",
        on_delete=models.CASCADE,
        related_name="contacts"
    )

    google_resource_name = models.CharField(
        max_length=255, null=True, blank=True
    )

    # Dados básicos
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    # Dados relacionais (CRM)
    source = models.CharField(
        max_length=50, default="Google"
    )  # google | instagram | indicacao | site

    status_relacional = models.CharField(
        max_length=30, default="contato"
    )  # contato | lead | paciente_ativo | paciente_inativo | parceiro

    arquivado = models.BooleanField(default=False)

    data_primeiro_contato = models.DateField(null=True, blank=True)
    data_ultimo_contato = models.DateField(null=True, blank=True)
    data_ultima_sessao = models.DateField(null=True, blank=True)

    observacoes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "google_resource_name")
        ordering = ["name"]

    def __str__(self):
        return self.name

from django.db import models


class Interacao(models.Model):
    TIPO_CHOICES = [
        ("mensagem", "Mensagem"),
        ("ligacao", "Ligação"),
        ("atendimento", "Atendimento"),
        ("avaliacao", "Avaliação"),
    ]

    pessoa = models.ForeignKey("crm.Contact", on_delete=models.CASCADE,related_name="interacoes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    descricao = models.TextField()
    data = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.pessoa.name}"

class AcaoPlanejada(models.Model):
    TIPO_CHOICES = [
        ("mensagem", "Mensagem"),
        ("ligacao", "Ligação"),
        ("retorno", "Retorno"),
        ("avaliacao", "Avaliação"),
    ]

    pessoa = models.ForeignKey("crm.Contact", on_delete=models.CASCADE, related_name="acoes_planejadas")

    tipo = models.CharField(  max_length=20,  choices=TIPO_CHOICES)

    descricao = models.TextField()

    data_planejada = models.DateTimeField()

    concluida = models.BooleanField(default=False)
    data_execucao = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["data_planejada"]

    def __str__(self):
        status = "✔" if self.concluida else "⏳"
        return f"{status} {self.get_tipo_display()} - {self.pessoa.name}"