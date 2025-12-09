from rest_framework import serializers
from .models import ( Usuário, ForcaMuscular, Mobilidade, Estabilidade, CategoriaTeste, TodosTestes, TesteFuncao, TesteDor, PreAvaliacao, Anamnese, 
                     Evento, Sessao)

class UsuarioBaseSerializer(serializers.ModelSerializer):
    """Serializer MÍNIMO para listas e operações básicas"""
    class Meta:
        model = Usuário
        fields = ['id', 'nome', 'organizacao']
        # Apenas campos NÃO sensíveis e essenciais
        read_only_fields = ['id', 'nome']

class UsuarioDetailSerializer(serializers.ModelSerializer):
    """Serializer COMPLETO apenas para operações que precisam de todos os dados"""
    
    class Meta:
        model = Usuário
        fields = '__all__'


class ForcaMuscularSerializer(serializers.ModelSerializer):
    movimento_forca_nome = serializers.CharField(source='movimento_forca.nome', read_only=True)

    class Meta:
        model = ForcaMuscular
        fields = '__all__'

class MobilidadeSerializer(serializers.ModelSerializer):
    nome_teste = serializers.CharField(source='nome.nome', read_only=True)  # <- pega o nome do FK

    class Meta:
        model = Mobilidade
        fields = '__all__'

class EstabilidadeSerializer(serializers.ModelSerializer):
    movimento_estabilidade_nome = serializers.CharField(source='movimento_estabilidade.nome', read_only=True)
    
    class Meta:
        model = Estabilidade
        fields = '__all__'

class CategoriaTesteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaTeste
        fields = ['id', 'nome']
        read_only_fields = ['id']

    def validate_nome(self, value):
        """
        Validação customizada para o campo nome
        """
        if not value.strip():
            raise serializers.ValidationError("O nome da categoria não pode estar vazio.")
        
        # Converte para title case para padronização
        return value.strip().title()

class TodosTestesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodosTestes
        fields = ['id', 'nome', 'categoria']  # campos do seu modelo TodosTestes

class TesteFuncaoSerializer(serializers.ModelSerializer):
    teste = serializers.PrimaryKeyRelatedField(queryset=TodosTestes.objects.all())
    teste_nome = serializers.CharField(source='teste.nome', read_only=True)


    class Meta:
        model = TesteFuncao
        fields = ['teste', 'teste_nome', 'id', 'data_avaliacao', 'lado_esquerdo', 'lado_direito', 'observacao', 'paciente']
    
class TesteDorSerializer(serializers.ModelSerializer):
    teste = serializers.PrimaryKeyRelatedField(queryset=TodosTestes.objects.all())
    teste_nome = serializers.CharField(source='teste.nome', read_only=True)

    class Meta:
        model = TesteDor
        fields = ['teste', 'teste_nome', 'id', 'data_avaliacao', 'resultado', 'observacao', 'paciente']

class PreAvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreAvaliacao
        fields = ['id', 'titulo', 'texto', 'clinica']

class AnamneseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anamnese
        fields = '__all__'

class EventoSerializer(serializers.ModelSerializer):
    paciente_nome = serializers.CharField(source='paciente.nome', read_only=True)  # nome do paciente vindo do related

    class Meta:
        model = Evento
        fields = '__all__'

class SessaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sessao
        fields = '__all__'