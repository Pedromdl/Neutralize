from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action

# 🔹 Models
from .models import Pasta, Secao, BancodeExercicio, Treino, TreinoExecutado, SerieRealizada, ExercicioExecutado, ExercicioPrescrito

# 🔹 Serializers
from .serializers import (
    PastaSerializer, SecaoSerializer, BancodeExercicioSerializer, TreinoSerializer, TreinoExecutadoSerializer, SerieRealizadaSerializer,
    ExercicioPrescritoSerializer, TreinoExecutadoCreateSerializer
)

# =========================
# Pastas
# =========================
class PastaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar Pastas de pacientes
    """
    serializer_class = PastaSerializer
    queryset = Pasta.objects.all()
    filterset_fields = ['paciente']  # já permite filtrar por paciente


    def get_queryset(self):
        # Filtra pastas por paciente se 'paciente' estiver nos query params
        paciente_id = self.request.query_params.get('paciente')
        if paciente_id:
            return Pasta.objects.filter(paciente__id=paciente_id)
        return self.queryset

# =========================
# Seções
# =========================
class SecaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar Seções de uma pasta
    """
    queryset = Secao.objects.all()
    serializer_class = SecaoSerializer

# =========================
# Orientações
# =========================
class BancodeExercicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar Bancos de Exercício
    """
    queryset = BancodeExercicio.objects.all()
    serializer_class = BancodeExercicioSerializer

class ExercicioPrescritoViewSet(viewsets.ModelViewSet):
    queryset = ExercicioPrescrito.objects.all()
    serializer_class = ExercicioPrescritoSerializer

    def get_queryset(self):
        treino_id = self.request.query_params.get('treino')
        if treino_id:
            return self.queryset.filter(treino_id=treino_id)
        return self.queryset

# =========================
# Treinos Interativos
# =========================
class TreinoViewSet(viewsets.ModelViewSet):
    queryset = Treino.objects.all()
    serializer_class = TreinoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        secao_id = self.request.query_params.get('secao')
        if secao_id:
            queryset = queryset.filter(secao_id=secao_id)
        return queryset

class TreinoExecutadoViewSet(viewsets.ModelViewSet):
    queryset = TreinoExecutado.objects.all().select_related("treino", "paciente").prefetch_related("exercicios__series")
    serializer_class = TreinoExecutadoSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        if paciente_id:
            return super().get_queryset().filter(paciente__id=paciente_id)
        return super().get_queryset()

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        treino = self.get_object()

        if not treino.paciente:
            return Response({'error': 'TreinoExecutado sem paciente.'}, status=400)

        # Atualiza treino
        treino.finalizado = True
        treino.tempo_total = request.data.get('tempo_total', treino.tempo_total)
        treino.data = request.data.get('data', treino.data)
        treino.save()

        series_data = request.data.get('series', [])

        if not series_data:
            return Response({'error': 'Nenhum exercício enviado.'}, status=400)

        erros = []
        for idx_ex, ex_data in enumerate(series_data):
            exercicio_id = ex_data.get('exercicio_id')
            if not exercicio_id:
                erros.append(f"Exercício {idx_ex} sem 'exercicio_id'.")
                continue

            try:
                # Cria ExercicioExecutado
                exercicio_executado = ExercicioExecutado.objects.create(
                    treino_executado=treino,
                    exercicio_id=exercicio_id,
                    rpe=ex_data.get('rpe')
                )
            except Exception as e:
                erros.append(f"Erro ao criar ExercicioExecutado {exercicio_id}: {str(e)}")
                continue

            # Valida e cria séries
            series_list = ex_data.get('series', [])
            if not series_list:
                erros.append(f"Exercício {exercicio_id} sem séries.")
                continue

            for s_idx, s in enumerate(series_list):
                try:
                    numero = s.get('numero')
                    repeticoes = s.get('repeticoes')
                    carga = s.get('carga')

                    if numero is None or repeticoes is None or carga is None:
                        erros.append(f"Série {s_idx+1} do exercício {exercicio_id} incompleta.")
                        continue

                    SerieRealizada.objects.create(
                        execucao=exercicio_executado,
                        exercicio=exercicio_executado.exercicio,
                        numero=numero,
                        repeticoes=repeticoes,
                        carga=carga
                    )
                except Exception as e:
                    erros.append(f"Erro na série {s_idx+1} do exercício {exercicio_id}: {str(e)}")

        serializer = self.get_serializer(treino)
        response_data = {'treino': serializer.data}
        if erros:
            response_data['erros'] = erros

        status_code = status.HTTP_200_OK if not erros else status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=status_code)



class SerieRealizadaViewSet(viewsets.ModelViewSet):
    queryset = SerieRealizada.objects.all().select_related("exercicio", "execucao")
    serializer_class = SerieRealizadaSerializer