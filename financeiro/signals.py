from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import TransacaoFinanceira, BancodeAtendimento, TransacaoOperacional
from eventos.models import EventoAgenda

print("✅ Signals do app Financeiro foram carregados com sucesso!")


# ============================================================
# 🔹 FUNÇÃO AUXILIAR
# ============================================================
def get_or_create_banco_para_paciente(paciente):
    banco, _ = BancodeAtendimento.objects.get_or_create(
        paciente=paciente,
        defaults={"saldo_atual": 0}
    )
    return banco


# ============================================================
# 🔸 1. Cria banco automaticamente antes de salvar transação financeira
# ============================================================
@receiver(pre_save, sender=TransacaoFinanceira)
def criar_banco_para_paciente(sender, instance, **kwargs):
    if not instance.banco and instance.paciente:
        print(f"[💰 PreSave] Criando banco para paciente {instance.paciente}")
        instance.banco = get_or_create_banco_para_paciente(instance.paciente)


# ============================================================
# 🔸 2. Atualiza saldo ao salvar TransacaoFinanceira
# ============================================================
@receiver(post_save, sender=TransacaoFinanceira)
def atualizar_saldo_por_tipo(sender, instance, created, **kwargs):
    banco = instance.banco
    if not banco:
        print(f"[⚠️ PostSave Financeira] Sem banco vinculado à transação {instance.id}")
        return

    print(f"[💸 PostSave Financeira] Tipo: {instance.tipo}, Num: {instance.num_atendimentos}, Saldo atual: {banco.saldo_atual}")

    if instance.tipo == "credito":
        banco.saldo_atual += instance.num_atendimentos
    elif instance.tipo == "debito":
        banco.saldo_atual -= instance.num_atendimentos

    banco.save()
    print(f"[💾 Saldo atualizado Financeira] Novo saldo: {banco.saldo_atual}")


# ============================================================
# 🔸 3. Ajusta saldo ao excluir transação financeira
# ============================================================
@receiver(post_delete, sender=TransacaoFinanceira)
def ajustar_saldo_exclusao(sender, instance, **kwargs):
    banco = instance.banco
    if not banco:
        print(f"[⚠️ Delete Financeira] Sem banco vinculado à transação {instance.id}")
        return

    print(f"[🗑️ Delete Financeira] Tipo: {instance.tipo}, Num: {instance.num_atendimentos}, Saldo antes: {banco.saldo_atual}")

    if instance.tipo == "credito":
        banco.saldo_atual -= instance.num_atendimentos
    elif instance.tipo == "debito":
        banco.saldo_atual += instance.num_atendimentos

    banco.save()
    print(f"[💾 Saldo após exclusão Financeira] Novo saldo: {banco.saldo_atual}")


# ============================================================
# 🔹 FUNÇÃO AUXILIAR (EVENTO)
# ============================================================
def get_or_create_banco(paciente):
    banco, _ = BancodeAtendimento.objects.get_or_create(
        paciente=paciente,
        defaults={"saldo_atual": 0}
    )
    return banco


# ============================================================
# 🔸 4. Salva status antigo do evento
# ============================================================
@receiver(pre_save, sender=EventoAgenda)
def salvar_status_antigo(sender, instance, **kwargs):
    if instance.pk:
        antigo = EventoAgenda.objects.filter(pk=instance.pk).first()
        instance._status_antigo = antigo.status if antigo else None
    else:
        instance._status_antigo = None

    print(f"[📋 PreSave Evento] ID={instance.id}, Status antigo={getattr(instance, '_status_antigo', None)}, Novo status={instance.status}")


# ============================================================
# 🔸 5. Atualiza saldo ao mudar status do evento
# ============================================================
@receiver(post_save, sender=EventoAgenda)
def atualizar_banco_ao_mudar_status_evento(sender, instance, created, **kwargs):
    print(f"\n[📅 PostSave Evento] Evento ID={instance.id}, Status={instance.status}, Criado={created}")
    status_antigo = getattr(instance, "_status_antigo", None)
    paciente = instance.paciente
    print(f"[👤 Paciente do evento] {paciente} | Status antigo={status_antigo}")

    if not paciente:
        print("[⚠️ Evento sem paciente vinculado]")
        return

    banco, _ = BancodeAtendimento.objects.get_or_create(paciente=paciente)
    print(f"[🏦 Banco encontrado] Saldo atual: {banco.saldo_atual}")

    if instance.status == "realizado" and status_antigo != "realizado":
        print("[🔻 Débito gerado por evento realizado]")
        TransacaoOperacional.objects.create(
            paciente=paciente,
            banco=banco,
            tipo="debito",
            num_atendimentos=1,
            descricao=f"Débito por evento {instance.id}",
        )

    elif status_antigo == "realizado" and instance.status != "realizado":
        print("[🔺 Crédito de reversão gerado (evento deixou de ser realizado)]")
        TransacaoOperacional.objects.create(
            paciente=paciente,
            banco=banco,
            tipo="credito",
            num_atendimentos=1,
            descricao=f"Crédito reversão do evento {instance.id}",
        )


# ============================================================
# 🔸 6. Atualiza saldo ao criar TransacaoOperacional
# ============================================================
@receiver(post_save, sender=TransacaoOperacional)
def atualizar_saldo_transacao(sender, instance, created, **kwargs):
    print(f"\n[⚙️ PostSave TransacaoOperacional] ID={instance.id}, Tipo={instance.tipo}, Criado={created}")

    if not created:
        print("[ℹ️ Transação existente - nada a fazer]")
        return

    if not instance.banco:
        print("[⚠️ Sem banco vinculado à transação operacional]")
        return

    print(f"[🏦 Banco antes] Paciente={instance.banco.paciente.nome}, Saldo={instance.banco.saldo_atual}")

    if instance.tipo == "credito":
        instance.banco.saldo_atual += instance.num_atendimentos
    elif instance.tipo == "debito":
        instance.banco.saldo_atual -= instance.num_atendimentos

    instance.banco.save()
    print(f"[💾 Banco após atualização] Novo saldo: {instance.banco.saldo_atual}")


# ============================================================
# 🔸 7. Reversão automática ao excluir evento
# ============================================================
@receiver(post_delete, sender=EventoAgenda)
def restaurar_sessao_ao_excluir_evento(sender, instance, **kwargs):
    print(f"[🗑️ Delete Evento] ID={instance.id}, Status={instance.status}")

    if instance.status == "realizado" and instance.paciente:
        banco, _ = BancodeAtendimento.objects.get_or_create(paciente=instance.paciente)
        print(f"[♻️ Revertendo saldo por exclusão de evento realizado] Saldo atual={banco.saldo_atual}")
        TransacaoOperacional.objects.create(
            paciente=instance.paciente,
            banco=banco,
            tipo="credito",
            num_atendimentos=1,
            descricao=f"Crédito por exclusão do evento {instance.id}",
        )
