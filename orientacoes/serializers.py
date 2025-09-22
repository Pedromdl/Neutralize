from rest_framework import serializers
from .models import Pasta, Secao, BancodeExercicio, Treino, ExercicioPrescrito, TreinoExecutado, SerieRealizada, ExercicioExecutado
from api.models import Usuário

class BancodeExercicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = BancodeExercicio
        fields = ["id", "titulo", "descricao", "video_url"]

class SecaoSerializer(serializers.ModelSerializer):
    orientacoes = serializers.SerializerMethodField()

    class Meta:
        model = Secao
        fields = ['id', 'titulo', 'pasta', 'orientacoes']

    def get_orientacoes(self, obj):
        # Aqui pegamos todos os exercícios da seção já pré-buscados
        resultados = []
        for treino in obj.treinos.all():
            for exercicio in treino.exercicios.all():
                resultados.append({
                    "id": exercicio.orientacao.id,
                    "titulo": exercicio.orientacao.titulo,
                    "descricao": exercicio.orientacao.descricao,
                    "video_url": exercicio.orientacao.video_url,
                    "treino_id": treino.id,
                    "treino_nome": treino.nome,
                })
        return resultados

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

class TreinoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Treino
        fields = ['id', 'nome', 'secao']

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
    # Mantém o serializer antigo para não quebrar nada
    series = SerieRealizadaSerializer(many=True, read_only=True)
    
    # Novo campo JSON
    seriess = serializers.JSONField(read_only=True)  # ou read/write conforme seu teste

    class Meta:
        model = ExercicioExecutado
        fields = ["id", "exercicio", "rpe", "series", "seriess"]

class TreinoExecutadoSerializer(serializers.ModelSerializer):
    exercicios = ExercicioExecutadoSerializer(many=True, read_only=True)
    treino = serializers.PrimaryKeyRelatedField(queryset=Treino.objects.all())
    treino_detalhes = TreinoListSerializer(source='treino', read_only=True)    # só para retorno
    paciente = serializers.PrimaryKeyRelatedField(queryset=Usuário.objects.all())

    class Meta:
        model = TreinoExecutado
        fields = ["id", "treino", "treino_detalhes", "paciente", "finalizado", "tempo_total", "data", "exercicios"]
        
class SerieGraficoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SerieRealizada
        fields = ['numero', 'repeticoes', 'carga']  # apenas o que interessa

class ExercicioGraficoSerializer(serializers.ModelSerializer):
    series = SerieGraficoSerializer(many=True)

    class Meta:
        model = ExercicioExecutado
        fields = ['id', 'exercicio', 'rpe', 'series']

class TreinoGraficoSerializer(serializers.ModelSerializer):
    exercicios = ExercicioGraficoSerializer(many=True)

    class Meta:
        model = TreinoExecutado
        fields = ['id', 'data', 'finalizado', 'exercicios']  # remove tempo_total

    
