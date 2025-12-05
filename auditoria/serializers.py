from rest_framework import serializers
from auditoria.models import AuditLog, Consentimento, RelatorioAcessoDados, PolíticaRetencaoDados


class ConsentimentoSerializer(serializers.ModelSerializer):
    """Serializer para gerenciar consentimentos LGPD"""
    class Meta:
        model = Consentimento
        fields = [
            'id', 'usuario', 'tipo', 'descricao', 'consentido',
            'data_consentimento', 'data_revogacao', 'ip_consentimento'
        ]
        read_only_fields = ['id', 'data_consentimento']


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de auditoria"""
    acao_display = serializers.CharField(source='get_acao_display', read_only=True)
    usuario_nome = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'usuario', 'usuario_nome', 'acao', 'acao_display',
            'modelo', 'objeto_id', 'timestamp', 'ip_address',
            'contem_dado_sensivel', 'removido'
        ]
        read_only_fields = [
            'id', 'timestamp', 'hash_integridade', 'dados_antes', 'dados_depois'
        ]
        filters_fields = ['usuario', 'acao', 'modelo', 'timestamp', 'ip_address']


class RelatorioAcessoDadosSerializer(serializers.ModelSerializer):
    """Serializer para relatórios de acesso LGPD Art. 18"""
    class Meta:
        model = RelatorioAcessoDados
        fields = [
            'id', 'usuario', 'data_geracao', 'data_inicio',
            'data_fim', 'acessos_registrados'
        ]
        read_only_fields = ['id', 'data_geracao']


class PolíticaRetencaoDadosSerializer(serializers.ModelSerializer):
    """Serializer para políticas de retenção"""
    tipo_acao_display = serializers.CharField(source='get_tipo_acao_display', read_only=True)

    class Meta:
        model = PolíticaRetencaoDados
        fields = [
            'id', 'tipo_acao', 'tipo_acao_display',
            'dias_retencao', 'descricao', 'ativo'
        ]
