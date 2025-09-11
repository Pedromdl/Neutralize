from rest_framework import serializers
from .models import Pasta, Secao, BancodeExercicio, Treino, ExercicioPrescrito, TreinoExecutado, SerieRealizada, ExercicioExecutado
from api.models import Usuário

class BancodeExercicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = BancodeExercicio
        fields = ["id", "titulo", "descricao", "video_url"]

class SecaoSerializer(serializers.ModelSerializer):
    orientacoes = BancodeExercicioSerializer(many=True, read_only=True)

    class Meta:
        model = Secao
        fields = ['id', 'titulo', 'pasta', 'orientacoes']

class PastaSerializer(serializers.ModelSerializer):
    secoes = SecaoSerializer(many=True, read_only=True)

    class Meta:
        model = Pasta
        fields = ['id', 'paciente', 'nome', 'secoes']
        read_only_fields = ['secoes']


class ExercicioPrescritoSerializer(serializers.ModelSerializer):
    orientacao_detalhes = BancodeExercicioSerializer(source='orientacao', read_only=True)

    class Meta:
        model = ExercicioPrescrito
        fields = ['id', 'treino', 'orientacao', 'orientacao_detalhes', 'series_planejadas', 'repeticoes_planejadas', 'carga_planejada', 'observacao']


class TreinoSerializer(serializers.ModelSerializer):
    exercicios = ExercicioPrescritoSerializer(many=True, read_only=True)

    class Meta:
        model = Treino
        fields = ['id', 'nome', 'secao', 'exercicios']


class SerieRealizadaSerializer(serializers.ModelSerializer):
    exercicio = ExercicioPrescritoSerializer(read_only=True)

    class Meta:
        model = SerieRealizada
        fields = ['exercicio', 'numero', 'repeticoes', 'carga']

class ExercicioExecutadoSerializer(serializers.ModelSerializer):
    series = SerieRealizadaSerializer(many=True, read_only=True)

    class Meta:
        model = ExercicioExecutado
        fields = ["id", "exercicio", "rpe", "series"]

class TreinoExecutadoSerializer(serializers.ModelSerializer):
    exercicios = ExercicioExecutadoSerializer(many=True, read_only=True)
    treino = serializers.PrimaryKeyRelatedField(queryset=Treino.objects.all())
    paciente = serializers.PrimaryKeyRelatedField(queryset=Usuário.objects.all())

    class Meta:
        model = TreinoExecutado
        fields = ["id", "treino", "paciente", "finalizado", "tempo_total", "data", "exercicios"]
        

class TreinoExecutadoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreinoExecutado
        fields = ["treino", "paciente"]  # os campos obrigatórios para criar

    def validate(self, data):
        # 🔹 Só para debug: mostra os dados que chegam
        print("Dados recebidos no serializer:", data)
        return data
    
class EvolucaoExercicioSerializer(serializers.Serializer):
    data = serializers.DateField()
    repeticoes = serializers.IntegerField()
    carga = serializers.FloatField()
    rpe = serializers.FloatField(allow_null=True)