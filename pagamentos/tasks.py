# pagamentos/tasks.py (usando Celery ou cron)
from django.utils import timezone
from datetime import timedelta
from pagamentos.models import Assinatura

def verificar_trial_expirado():
    """Verifica assinaturas com trial expirado"""
    hoje = timezone.now()
    
    assinaturas_expiradas = Assinatura.objects.filter(
        status='trial',
        data_fim_trial__lte=hoje
    )
    
    for assinatura in assinaturas_expiradas:
        # Muda status para "aguardando pagamento"
        assinatura.status = 'aguardando_pagamento'
        assinatura.save()
        
        # 🔥 ENVIAR EMAIL/NOTIFICAÇÃO solicitando cartão
        enviar_solicitacao_cartao(assinatura)

def enviar_solicitacao_cartao(assinatura):
    """Envia notificação para cadastrar cartão"""
    # Implementar: Email, notificação no sistema, etc.
    print(f"🔔 Solicitar cartão para: {assinatura.clinica.nome}")