from rest_framework import serializers
from crm.models import Contact, Interacao, AcaoPlanejada

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "name", "phone", "email", "arquivado", "status_relacional", "data_ultimo_contato", "data_ultima_sessao"]

class ContactStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["status_relacional"]

class InteracaoSerializer(serializers.ModelSerializer):
    tipo_label = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Interacao
        fields = ["id", "tipo", "tipo_label", "descricao", "data",]

class AcaoPlanejadaSerializer(serializers.ModelSerializer):
    pessoa_name = serializers.CharField(source="pessoa.name", read_only=True)

    class Meta:
        model = AcaoPlanejada
        fields = ["id", "pessoa_name", "pessoa", "tipo", "descricao", "data_planejada", "concluida", "data_execucao", "created_at", "updated_at",]
        read_only_fields = ["id", "concluida", "data_execucao", "created_at", "updated_at"]