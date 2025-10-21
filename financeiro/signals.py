from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import TransacaoFinanceira, BancodeAtendimento, TransacaoOperacional
from eventos.models import EventoAgenda

# Função auxiliar para criar banco se não existir
def get_or_create_banco_para_paciente(paciente):
    banco, _ = BancodeAtendimento.objects.get_or_create(
        paciente=paciente,
        defaults={"saldo_atual": 0}
    )
    return banco

# Cria banco automaticamente se não houver
@receiver(pre_save, sender=TransacaoFinanceira)
def criar_banco_para_paciente(sender, instance, **kwargs):
    if not instance.banco and instance.paciente:
        instance.banco = get_or_create_banco_para_paciente(instance.paciente)

# Atualiza saldo ao salvar transação (sempre pelo tipo)
@receiver(post_save, sender=TransacaoFinanceira)
def atualizar_saldo_por_tipo(sender, instance, created, **kwargs):
    banco = instance.banco
    if not banco:
        return

    # Ajusta saldo do banco conforme tipo
    if instance.tipo == "credito":
        banco.saldo_atual += instance.num_atendimentos
    elif instance.tipo == "debito":
        banco.saldo_atual -= instance.num_atendimentos

    banco.save()

# Ajusta saldo ao excluir transação
@receiver(post_delete, sender=TransacaoFinanceira)
def ajustar_saldo_exclusao(sender, instance, **kwargs):
    banco = instance.banco
    if not banco:
        return

    if instance.tipo == "credito":
        banco.saldo_atual -= instance.num_atendimentos
    elif instance.tipo == "debito":
        banco.saldo_atual += instance.num_atendimentos

    banco.save()



#------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------
# --------------------------
# Função auxiliar
# --------------------------
def get_or_create_banco(paciente):
    banco, _ = BancodeAtendimento.objects.get_or_create(
        paciente=paciente,
        defaults={"saldo_atual": 0}
    )
    return banco

# -----------------------------
# 1️⃣ Salva status antigo
# -----------------------------
@receiver(pre_save, sender=EventoAgenda)
def salvar_status_antigo(sender, instance, **kwargs):
    if instance.pk:
        antigo = EventoAgenda.objects.filter(pk=instance.pk).first()
        instance._status_antigo = antigo.status if antigo else None
    else:
        instance._status_antigo = None


# -----------------------------
# 2️⃣ Atualiza saldo ao mudar status
# -----------------------------
@receiver(post_save, sender=EventoAgenda)
def atualizar_banco_ao_mudar_status_evento(sender, instance, created, **kwargs):
    print(f"Post_save disparado: {instance.id}, status={instance.status}")

    status_antigo = getattr(instance, "_status_antigo", None)
    paciente = instance.paciente
    if not paciente:
        return

    banco, _ = BancodeAtendimento.objects.get_or_create(paciente=paciente)

    # Caso 1: Novo status é "realizado" → cria DÉBITO
    if instance.status == "realizado" and status_antigo != "realizado":
        TransacaoOperacional.objects.create(
            paciente=paciente,
            banco=banco,
            tipo="debito",
            num_atendimentos=1,
            descricao=f"Débito por evento {instance.id}",
        )

    # Caso 2: Antigo era "realizado" e novo não é → cria CRÉDITO (reversão)
    elif status_antigo == "realizado" and instance.status != "realizado":
        TransacaoOperacional.objects.create(
            paciente=paciente,
            banco=banco,
            tipo="credito",
            num_atendimentos=1,
            descricao=f"Crédito reversão do evento {instance.id}",
        )


# -----------------------------
# 3️⃣ Atualiza saldo ao criar TransacaoOperacional
# -----------------------------
@receiver(post_save, sender=TransacaoOperacional)
def atualizar_saldo_transacao(sender, instance, created, **kwargs):
    if not created or not instance.banco:
        return

    if instance.tipo == "credito":
        instance.banco.saldo_atual += instance.num_atendimentos
    elif instance.tipo == "debito":
        instance.banco.saldo_atual -= instance.num_atendimentos

    instance.banco.save()


# -----------------------------
# 4️⃣ Reversão automática ao excluir evento
# -----------------------------
@receiver(post_delete, sender=EventoAgenda)
def restaurar_sessao_ao_excluir_evento(sender, instance, **kwargs):
    if instance.status == "realizado" and instance.paciente:
        banco, _ = BancodeAtendimento.objects.get_or_create(paciente=instance.paciente)
        TransacaoOperacional.objects.create(
            paciente=instance.paciente,
            banco=banco,
            tipo="credito",
            num_atendimentos=1,
            descricao=f"Crédito por exclusão do evento {instance.id}",
        )