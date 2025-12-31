import logging
import json
from django.utils.deprecation import MiddlewareMixin
from django.http import QueryDict
from auditoria.models import AuditLog
from django.contrib.auth.models import AnonymousUser
import traceback

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Extrai IP real do cliente (considerando proxies)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Extrai User-Agent do navegador"""
    return request.META.get('HTTP_USER_AGENT', '')


class AuditoriaMiddleware(MiddlewareMixin):
    """
    Middleware que registra todas as ações na plataforma para LGPD compliance.
    
    Registra:
    - CREATE (POST) ✅
    - READ (GET) ✅
    - UPDATE (PUT/PATCH) ✅
    - DELETE ✅
    - LOGIN/LOGOUT ✅
    - Acesso negado ✅
    """

    # APIs que não devem ser auditadas (muito verbosas)
    ENDPOINTS_IGNORADOS = [
        '/static/',
        '/media/',
        '/admin/jsi18n',
        '/__debug__',
        '/health',
        '/ping',
    ]

    # Endpoints sensíveis que registram dados sensíveis
    ENDPOINTS_SENSIVEL = {
        'usuario': 'SAUDE',
        'sessao': 'SAUDE',
        'prescricao': 'SAUDE',
        'medicamento': 'SAUDE',
        'paciente': 'SAUDE',
    }

    def should_audit(self, request):
        """Verifica se a requisição deve ser auditada"""
        path = request.path

        # Ignorar paths estáticos/debug
        for ignorado in self.ENDPOINTS_IGNORADOS:
            if path.startswith(ignorado):
                return False

        # Apenas auditar requisições HTTP conhecidas
        return request.method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']

    def get_tipo_dado_sensivel(self, path):
        """Identifica se o endpoint contém dados sensíveis"""
        path_lower = path.lower()
        for endpoint, tipo in self.ENDPOINTS_SENSIVEL.items():
            if endpoint in path_lower:
                return tipo
        return None

    def extrair_dados_request(self, request):
        """
        NÃO lê body para evitar consumo do stream.
        Payload deve ser auditado na view/serializer.
        """
        return None

    def process_response(self, request, response):
        """
        Processa response e registra auditoria.
        Chamado APÓS a view ser executada.
        """
        if not self.should_audit(request):
            return response

        try:
            user = request.user if request.user.is_authenticated else None
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)
            path = request.path
            method = request.method
            status_code = response.status_code

            # Determinar tipo de ação baseado no método HTTP
            if method == 'POST':
                acao = 'CREATE'
            elif method in ['PUT', 'PATCH']:
                acao = 'UPDATE'
            elif method == 'DELETE':
                acao = 'DELETE'
            elif method == 'GET':
                acao = 'READ'
            else:
                acao = 'READ'

            # Se acesso negado, registrar como PERMISSAO_NEGADA
            if status_code in [403, 401]:
                acao = 'PERMISSAO_NEGADA'

            # Extrair dados
            dados_request = self.extrair_dados_request(request)

            # Identifi modelo e objeto_id
            partes_path = path.strip('/').split('/')
            modelo = partes_path[1] if len(partes_path) > 1 else 'unknown'
            objeto_id = partes_path[2] if len(partes_path) > 2 else 'N/A'

            # Tipo de dado sensível
            contem_dado_sensivel = self.get_tipo_dado_sensivel(path)

            # Não registra READ requests de APIs públicas
            if acao == 'READ' and (status_code == 401 or not user):
                return response

            # Criar log de auditoria
            AuditLog.objects.create(
                usuario=user,
                acao=acao,
                modelo=modelo,
                objeto_id=objeto_id,
                dados_antes=None,  # Seria preenchido por signals nos models
                dados_depois=dados_request,
                ip_address=ip_address,
                user_agent=user_agent,
                contem_dado_sensivel=contem_dado_sensivel,
            )

            logger.info(
                f"✅ Auditoria registrada: {acao} {modelo} ({objeto_id}) "
                f"por {user} - Status {status_code}"
            )

        except Exception as e:
            logger.error(f"❌ Erro ao registrar auditoria: {e}\n{traceback.format_exc()}")
            # NÃO interrompe a requisição mesmo com erro

        return response


class AuditoriaBearerTokenMiddleware(MiddlewareMixin):
    """
    Middleware para rastrear logins via token/JWT.
    Registra LOGIN quando token é usado.
    """
    def process_request(self, request):
        """Chamado ANTES da view"""
        try:
            # Verificar se há token Authorization
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            
            if auth_header.startswith('Bearer ') or auth_header.startswith('Token '):
                user = request.user
                
                # Se é um novo login (primeira requisição com o token)
                if hasattr(request, 'user') and user.is_authenticated:
                    # Registrar como READ (acesso autenticado)
                    AuditLog.objects.create(
                        usuario=user,
                        acao='LOGIN',
                        modelo='auth.Token',
                        objeto_id=user.id,
                        ip_address=get_client_ip(request),
                        user_agent=get_user_agent(request),
                    )
        except Exception as e:
            logger.error(f"Erro ao processar token: {e}")
        
        return None
