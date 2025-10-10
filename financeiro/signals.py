from django.db.models.signals import post_save
from django.dispatch import receiver
from eventos.models import EventoAgenda
from .models import LancamentoFinanceiro

@receiver(post_save, sender=EventoAgenda)
def criar_ou_remover_lancamento_financeiro(sender, instance, created, **kwargs):
    if instance.status == "realizado" and instance.paciente:
        LancamentoFinanceiro.objects.get_or_create(
            evento=instance,
            defaults={
                "paciente": instance.paciente,
                "valor": 0,
                "tipo_servico": instance.tipo,
            }
        )
    else:
        # Se não está realizado, remove o lançamento vinculado (se existir)
        LancamentoFinanceiro.objects.filter(evento=instance).delete()
