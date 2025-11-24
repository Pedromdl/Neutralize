# from rest_framework import permissions
# from django.http import JsonResponse

# class TrialNotExpiredPermission(permissions.BasePermission):
#     """
#     Permissão que bloqueia acesso se trial expirado
#     """
    
#     def has_permission(self, request, view):
#         # URLs que SEMPRE são permitidas (mesmo com trial expirado)
#         URLs_PERMITIDAS = [
#             '/api/auth/',
#             '/api/assinatura/',
#             '/api/pagamentos/',
#             '/admin/',
#             '/logout/',
#         ]
        
#         # Se a URL atual está na lista permitida, libera
#         if any(request.path.startswith(url) for url in URLs_PERMITIDAS):
#             return True
            
#         # Verifica se usuário está autenticado e tem clínica
#         if not (request.user and request.user.is_authenticated and hasattr(request.user, 'clinica')):
#             return True  # Ou False, dependendo do seu caso
            
#         try:
#             # Verifica assinatura
#             assinatura = getattr(request.user.clinica, 'assinatura_pagamento', None)
#             if assinatura and assinatura.precisa_pagamento:
#                 # 🚫 BLOQUEIA ACESSO - Trial expirado
#                 # Em vez de retornar False, vamos levantar uma exceção customizada
#                 from rest_framework.exceptions import PermissionDenied
#                 raise PermissionDenied({
#                     'error': 'Trial expirado',
#                     'message': 'Seu período trial acabou. Cadastre um cartão para continuar usando o sistema.',
#                     'status': 'aguardando_pagamento',
#                     'assinatura_id': assinatura.id
#                 })
                
#             return True
            
#         except Exception:
#             return True  # Em caso de erro, libera o acesso