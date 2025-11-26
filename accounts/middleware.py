# accounts/middleware.py
from django.utils import timezone
from django.http import JsonResponse
from httpcore import request

class TrialExpirationMiddleware:
    """Verifica e expira trials automaticamente"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"🎯 DEBUG MIDDLEWARE - User: {request.user}, Auth: {request.user.is_authenticated}")
        print(f"🎯 DEBUG MIDDLEWARE - Path: {request.path}")
        # Só verifica se usuário está autenticado e tem clínica
        if request.user.is_authenticated and hasattr(request.user, 'organizacao'):
            try:
                assinatura = getattr(request.user.organizacao, 'assinatura_pagamento', None)
                if assinatura and assinatura.status == 'trial' and not assinatura.em_trial:
                    # 🔥 EXPIRA O TRIAL AUTOMATICAMENTE
                    assinatura.expirar_trial()
                    print(f"✅ Trial expirado para: {request.user.organizacao.nome}")
            except Exception as e:
                print(f"❌ Erro ao verificar trial: {e}")
                
        response = self.get_response(request)
        return response
   # accounts/middleware.py - ADICIONE ESTES PRINTS:

class TrialAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"🔍 TrialAccessMiddleware - URL: {request.path}")
        print(f"🔍 Usuário autenticado: {request.user.is_authenticated}")
        
        # Lista de URLs permitidas mesmo com trial expirado
        URLs_PERMITIDAS = [
            '/admin/',
            '/api/auth/',
            '/api/assinatura/',
            '/api/pagamentos/',
            '/logout/',
        ]
        
        print(f"🔍 URLs permitidas: {URLs_PERMITIDAS}")
        
        # Verifica se precisa bloquear
        if (request.user.is_authenticated and 
            hasattr(request.user, 'organizacao')):
            
            print(f"🔍 Usuário tem clínica: {request.user.organizacao.nome}")
            
            if not any(request.path.startswith(url) for url in URLs_PERMITIDAS):
                print(f"🔍 URL NÃO está na lista permitida: {request.path}")
                
                try:
                    assinatura = getattr(request.user.organizacao, 'assinatura_pagamento', None)
                    print(f"🔍 Assinatura encontrada: {assinatura}")
                    
                    if assinatura:
                        print(f"🔍 Status da assinatura: {assinatura.status}")
                        print(f"🔍 Precisa pagamento? {assinatura.precisa_pagamento}")
                        
                        if assinatura.precisa_pagamento:
                            print(f"🚫 BLOQUEANDO ACESSO para: {request.path}")
                            return JsonResponse({
                                'error': 'Trial expirado',
                                'message': 'Seu período trial acabou. Cadastre um cartão para continuar usando o sistema.',
                                'status': 'aguardando_pagamento',
                                'assinatura_id': assinatura.id
                            }, status=402)
                    else:
                        print("🔍 Nenhuma assinatura encontrada")
                        
                except Exception as e:
                    print(f"❌ Erro ao verificar acesso: {e}")
            else:
                print(f"✅ URL PERMITIDA: {request.path}")
        else:
            print(f"🔍 Usuário não autenticado ou sem clínica")
                
        return self.get_response(request)