from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count
from django.utils import timezone
from datetime import datetime, timedelta
import hashlib
import json

from auditoria.models import (
    AuditLog, Consentimento, RelatorioAcessoDados,
    PolíticaRetencaoDados
)
from auditoria.serializers import (
    AuditLogSerializer, ConsentimentoSerializer,
    RelatorioAcessoDadosSerializer, PolíticaRetencaoDadosSerializer
)


class ConsentimentoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar consentimentos LGPD.
    Endpoint: /api/auditoria/consentimentos/
    
    Implementa LGPD Art. 7, I: "Consentimento livre, informado e revogável"
    """
    serializer_class = ConsentimentoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Cada usuário vê apenas seus consentimentos"""
        user = self.request.user
        return Consentimento.objects.filter(usuario=user)

    def perform_create(self, serializer):
        """Registra consentimento do usuário logado"""
        serializer.save(
            usuario=self.request.user,
            ip_consentimento=self._get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def revogar(self, request, pk=None):
        """
        Revoga um consentimento (LGPD Art. 8)
        POST /api/auditoria/consentimentos/{id}/revogar/
        """
        consentimento = self.get_object()
        
        # Verificar se é o usuário logado
        if consentimento.usuario != request.user:
            return Response(
                {'erro': 'Você não pode revogar consentimento de outro usuário'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        consentimento.revogar()
        return Response(
            {'mensagem': f'Consentimento "{consentimento.get_tipo_display()}" revogado com sucesso.'},
            status=status.HTTP_200_OK
        )

    def _get_client_ip(self):
        """Extrai IP do cliente"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return self.request.META.get('REMOTE_ADDR')


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para visualizar logs de auditoria.
    Endpoint: /api/auditoria/logs/
    
    Implementa LGPD Art. 5, XII: "Rastreabilidade"
    
    Apenas administradores podem acessar todos os logs.
    Usuários normais podem acessar seus próprios logs.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtro por permissão:
        - Admin: vê TODOS os logs
        - User: vê apenas logs onde ele é o usuário
        """
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return AuditLog.objects.all()
        else:
            return AuditLog.objects.filter(usuario=user)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def por_usuario(self, request):
        """
        Retorna logs filtrados por usuário (admin only)
        GET /api/auditoria/logs/por_usuario/?usuario_id=123
        """
        usuario_id = request.query_params.get('usuario_id')
        
        if not usuario_id:
            return Response(
                {'erro': 'Parâmetro usuario_id é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = AuditLog.objects.filter(usuario_id=usuario_id).order_by('-timestamp')
        serializer = self.get_serializer(logs, many=True)
        
        return Response({
            'usuario_id': usuario_id,
            'total_acessos': logs.count(),
            'logs': serializer.data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def por_periodo(self, request):
        """
        Retorna logs em um período específico (admin only)
        GET /api/auditoria/logs/por_periodo/?data_inicio=2024-01-01&data_fim=2024-01-31
        """
        data_inicio = request.query_params.get('data_inicio')
        data_fim = request.query_params.get('data_fim')
        
        try:
            dt_inicio = datetime.fromisoformat(data_inicio).replace(hour=0, minute=0, second=0)
            dt_fim = datetime.fromisoformat(data_fim).replace(hour=23, minute=59, second=59)
        except (ValueError, TypeError):
            return Response(
                {'erro': 'Datas inválidas. Use formato ISO (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = AuditLog.objects.filter(
            timestamp__gte=dt_inicio,
            timestamp__lte=dt_fim
        ).order_by('-timestamp')
        
        serializer = self.get_serializer(logs, many=True)
        
        return Response({
            'periodo': f'{data_inicio} a {data_fim}',
            'total_acessos': logs.count(),
            'logs': serializer.data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def suspeitos(self, request):
        """
        Retorna logs suspeitos (múltiplos acessos negados, IPs diferentes, etc)
        GET /api/auditoria/logs/suspeitos/
        """
        # Acessos negados em uma hora
        uma_hora_atras = timezone.now() - timedelta(hours=1)
        tentativas_negadas = AuditLog.objects.filter(
            acao='PERMISSAO_NEGADA',
            timestamp__gte=uma_hora_atras
        ).values('usuario', 'ip_address').distinct()
        
        logs_suspeitos = AuditLog.objects.filter(
            acao__in=['PERMISSAO_NEGADA', 'DELETE'],
            timestamp__gte=uma_hora_atras
        ).order_by('-timestamp')
        
        serializer = self.get_serializer(logs_suspeitos, many=True)
        
        return Response({
            'alertas': list(tentativas_negadas),
            'total_suspeito': logs_suspeitos.count(),
            'logs': serializer.data
        })


class RelatorioAcessoDadosViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerar e visualizar relatórios de acesso.
    Endpoint: /api/auditoria/relatorios/
    
    Implementa LGPD Art. 18: "Direito de acesso do titular de dados"
    
    Usuários podem requisitar relatório de quem acessou seus dados.
    """
    serializer_class = RelatorioAcessoDadosSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Cada usuário vê apenas seus relatórios"""
        user = self.request.user
        if user.is_staff:
            return RelatorioAcessoDados.objects.all()
        return RelatorioAcessoDados.objects.filter(usuario=user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def gerar_relatorio(self, request):
        """
        Gera relatório de "Quem acessou meus dados" (LGPD Art. 18)
        POST /api/auditoria/relatorios/gerar_relatorio/
        
        Body (optional):
        {
            "data_inicio": "2024-01-01",
            "data_fim": "2024-01-31"
        }
        """
        user = request.user
        
        # Parse datas
        data_inicio_str = request.data.get(
            'data_inicio',
            (timezone.now() - timedelta(days=30)).date().isoformat()
        )
        data_fim_str = request.data.get('data_fim', timezone.now().date().isoformat())
        
        try:
            dt_inicio = datetime.fromisoformat(data_inicio_str)
            dt_fim = datetime.fromisoformat(data_fim_str)
        except ValueError:
            return Response(
                {'erro': 'Datas inválidas. Use formato ISO (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar todos os acessos ao usuário no período
        acessos = AuditLog.objects.filter(
            objeto_id=str(user.id),
            timestamp__gte=dt_inicio,
            timestamp__lte=dt_fim
        ).exclude(usuario=user)  # Não contar o acesso do próprio usuário
        
        # Calcular hash de integridade
        dados_relatorio = f"{user.id}{dt_inicio}{dt_fim}{acessos.count()}"
        hash_integridade = hashlib.sha256(dados_relatorio.encode()).hexdigest()
        
        # Criar relatório
        relatorio = RelatorioAcessoDados.objects.create(
            usuario=user,
            data_inicio=dt_inicio,
            data_fim=dt_fim,
            acessos_registrados=acessos.count(),
            hash_integridade=hash_integridade
        )
        
        # Serializar logs de acesso
        logs_serializados = AuditLogSerializer(acessos, many=True).data
        
        serializer = self.get_serializer(relatorio)
        
        return Response({
            'relatorio': serializer.data,
            'acessos_detalhados': logs_serializados,
            'resumo': {
                'periodo': f'{dt_inicio.date()} a {dt_fim.date()}',
                'total_acessos': acessos.count(),
                'acessos_por_tipo': dict(
                    acessos.values('acao').annotate(
                        count=Count('id')
                    ).values_list('acao', 'count')
                )
            }
        })


class DireitoEsquecimentoViewSet(viewsets.ViewSet):
    """
    Implementa direito ao esquecimento (LGPD Art. 17)
    Endpoint: /api/auditoria/direito-esquecimento/
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def solicitar_anonimizacao(self, request):
        """
        Solicita anonimização de dados pessoais do usuário
        POST /api/auditoria/direito-esquecimento/solicitar_anonimizacao/
        
        Body:
        {
            "motivo": "Quero ser esquecido",
            "dados_deletar": ["logs_completos", "consentimentos"]
        }
        """
        user = request.user
        motivo = request.data.get('motivo', 'Não informado')
        
        # Anonimizar todos os logs do usuário
        logs = AuditLog.objects.filter(usuario=user)
        count = logs.count()
        
        for log in logs:
            log.anonimizar()
        
        # Opcionalmente, revogar todos os consentimentos
        consentimentos = Consentimento.objects.filter(usuario=user, consentido=True)
        consentimentos.update(consentido=False, data_revogacao=timezone.now())
        
        return Response({
            'mensagem': 'Direito ao esquecimento processado com sucesso',
            'dados_anonimizados': count,
            'consentimentos_revogados': consentimentos.count(),
            'motivo': motivo,
            'data_processamento': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def status_anonimizacao(self, request):
        """
        Verifica status da anonimização do usuário
        GET /api/auditoria/direito-esquecimento/status_anonimizacao/
        """
        user = request.user
        
        logs_anonimizados = AuditLog.objects.filter(usuario__isnull=True, removido=True).count()
        logs_ativos = AuditLog.objects.filter(usuario=user, removido=False).count()
        
        return Response({
            'usuario': user.username,
            'logs_anonimizados': logs_anonimizados,
            'logs_ativos': logs_ativos,
            'status': 'Anonimizado' if logs_ativos == 0 else 'Parcialmente anonimizado'
        })


class PolíticaRetencaoDadosViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar políticas de retenção LGPD.
    Endpoint: /api/auditoria/politicas-retencao/
    
    Apenas administradores podem acessar.
    """
    queryset = PolíticaRetencaoDados.objects.all()
    serializer_class = PolíticaRetencaoDadosSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['post'])
    def limpar_logs_expirados(self, request):
        """
        Deleta automaticamente logs que passaram da data de retenção.
        POST /api/auditoria/politicas-retencao/limpar_logs_expirados/
        
        CUIDADO: Esta operação é irreversível!
        """
        agora = timezone.now()
        
        # Buscar logs que expiraram
        logs_expirados = AuditLog.objects.filter(
            data_retencao__lt=agora,
            removido=False
        )
        
        count = logs_expirados.count()
        
        # Anonimizar ao invés de deletar (melhores práticas LGPD)
        for log in logs_expirados:
            log.anonimizar()
        
        return Response({
            'mensagem': 'Limpeza de logs expirados concluída',
            'logs_anonimizados': count,
            'data_execucao': agora.isoformat()
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def relatorio_retencao(self, request):
        """
        Relatório de retenção de dados
        GET /api/auditoria/politicas-retencao/relatorio_retencao/
        """
        agora = timezone.now()
        
        logs_ativos = AuditLog.objects.filter(
            data_retencao__gte=agora,
            removido=False
        ).count()
        
        logs_proximos_vencer = AuditLog.objects.filter(
            data_retencao__gte=agora,
            data_retencao__lt=agora + timedelta(days=7),
            removido=False
        ).count()
        
        logs_expirados = AuditLog.objects.filter(
            data_retencao__lt=agora,
            removido=False
        ).count()
        
        logs_anonimizados = AuditLog.objects.filter(
            removido=True
        ).count()
        
        return Response({
            'resumo_retencao': {
                'logs_ativos': logs_ativos,
                'logs_proximos_expirar': logs_proximos_vencer,
                'logs_expirados': logs_expirados,
                'logs_anonimizados': logs_anonimizados
            },
            'data_relatorio': agora.isoformat()
        })
