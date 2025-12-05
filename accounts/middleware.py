# accounts/middleware.py
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone


class TrialExpirationMiddleware(MiddlewareMixin):
    """Verifica automaticamente se o trial expirou e atualiza o status."""

    def process_request(self, request):
        print(f"🎯 TrialExpirationMiddleware - User: {request.user}")
        
        if not request.user.is_authenticated:
            return

        org = getattr(request.user, "organizacao", None)
        if org is None:
            return

        try:
            # CORREÇÃO: Usa assinatura_pagamento.all() para ForeignKey
            assinatura = org.assinatura_pagamento.all().order_by('-id').first()
            
            if assinatura and assinatura.status == "trial" and not assinatura.em_trial:
                assinatura.expirar_trial()
                print(f"🔥 Trial expirado automaticamente para: {org.nome}")

        except Exception as e:
            print(f"❌ Erro ao expirar trial: {e}")


# accounts/middleware.py
class TrialAccessMiddleware(MiddlewareMixin):
    """Bloqueia acesso quando trial expirou ou pagamento está pendente."""
    
    URLs_PERMITIDAS = [
        "/admin/",
        "/api/auth/",
        "/api/assinatura/",
        "/api/pagamentos/",
        "/logout/",
    ]
    
    def process_request(self, request):
        path = request.path
        
        # URLs permitidas
        if any(path.startswith(url) for url in self.URLs_PERMITIDAS):
            return
        
        if not request.user.is_authenticated:
            return
        
        org = getattr(request.user, "organizacao", None)
        if org is None:
            return
        
        try:
            # 🔥 MELHORIA: Busca na ORDEM CORRETA de prioridade
            assinatura = None
            
            # 1️⃣ Primeiro tenta encontrar assinatura ATIVA
            assinatura = org.assinatura_pagamento.filter(
                status="ativa"
            ).order_by('-data_inicio').first()
            
            # 2️⃣ Se não tem ativa, busca TRIAL (ainda válido)
            if not assinatura:
                assinatura = org.assinatura_pagamento.filter(
                    status="trial"
                ).order_by('-data_inicio').first()
            
            # 3️⃣ Se não tem ativa nem trial, pega a mais recente (para histórico)
            if not assinatura:
                assinatura = org.assinatura_pagamento.all().order_by('-data_inicio').first()
            
            print(f"🔍 Assinatura selecionada: ID={assinatura.id if assinatura else 'Nenhuma'}, "
                  f"Status={assinatura.status if assinatura else 'N/A'}")
            
            if not assinatura:
                print("🔍 Nenhuma assinatura → acesso permitido")
                return
            
            # 🔥 ATUALIZAÇÃO DE STATUS (importante para trial expirado)
            if hasattr(assinatura, 'atualizar_expiracao'):
                assinatura.atualizar_expiracao()
                # Recarrega do banco para pegar status atualizado
                assinatura.refresh_from_db()
            
            # 🔥 LÓGICA DE BLOQUEIO MELHORADA
            deve_bloquear = False
            motivo = ""
            
            if assinatura.status == "aguardando_pagamento":
                deve_bloquear = True
                motivo = "Pagamento pendente após trial"
            
            elif assinatura.status == "expirada":
                deve_bloquear = True
                motivo = "Assinatura expirada"
            
            elif assinatura.status == "cancelada":
                # 🔥 GRACE PERIOD: Acesso mantido até data_proximo_pagamento
                hoje = timezone.now().date()
                if assinatura.data_proximo_pagamento:
                    if hoje > assinatura.data_proximo_pagamento.date():
                        deve_bloquear = True
                        motivo = "Período de acesso pós-cancelamento expirado"
                    else:
                        # Ainda dentro do grace period
                        dias_restantes = (assinatura.data_proximo_pagamento.date() - hoje).days
                        print(f"✅ Acesso permitido (cancelada, mas dentro do grace period: {dias_restantes} dias restantes)")
                        return
                else:
                    # Sem data definida, bloqueia imediatamente
                    deve_bloquear = True
                    motivo = "Assinatura cancelada sem data de término"
            
            elif assinatura.status == "suspensa":
                deve_bloquear = True
                motivo = "Assinatura suspensa por falta de pagamento"
            
            # 🔥 APLICA BLOQUEIO SE NECESSÁRIO
            if deve_bloquear:
                print(f"🚫 BLOQUEANDO ACESSO: {motivo}")
                return JsonResponse({
                    "error": "Acesso bloqueado",
                    "message": f"{motivo}. Ative sua assinatura para continuar.",
                    "status": assinatura.status,
                    "assinatura_id": assinatura.id,
                    "data_proximo_pagamento": assinatura.data_proximo_pagamento.isoformat() if assinatura.data_proximo_pagamento else None,
                    "url_ativacao": f"/api/pagamentos/assinatura/{assinatura.id}/ativar-com-cartao/"
                }, status=402)
            
            print(f"✅ Acesso liberado: Status={assinatura.status}")
            
        except Exception as e:
            print(f"❌ Erro no middleware: {e}")
            import traceback
            traceback.print_exc()