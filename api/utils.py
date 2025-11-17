from .models import DataAccessLog

def log_acesso(usuario, paciente_id, acao, campo, request=None, detalhes=None):
    ip = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    tenant = getattr(usuario, "tenant", None)  # identifica a clínica

    # Criação do log
    DataAccessLog.objects.create(
        usuario=usuario,
        paciente_id=paciente_id,
        acao=acao,
        campo=campo,
        ip=ip,
        detalhes=detalhes,
    )
