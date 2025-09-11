from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action

# 🔹 Models
from .models import Pasta, Secao, BancodeExercicio, Treino, TreinoExecutado, SerieRealizada, ExercicioExecutado, ExercicioPrescrito
from api.models import Usuário
# 🔹 Serializers
from .serializers import (
    PastaSerializer, SecaoSerializer, BancodeExercicioSerializer, TreinoSerializer, TreinoExecutadoSerializer, SerieRealizadaSerializer,
    ExercicioPrescritoSerializer, TreinoGraficoSerializer
)

# =========================
# Pastas
# =========================
class PastaViewSet(viewsets.ModelViewSet):
    serializer_class = PastaSerializer
    queryset = Pasta.objects.all()

    def get_queryset(self):
        # fluxo profissional: se query param 'paciente' estiver presente
        paciente_param = self.request.query_params.get("paciente")
        if paciente_param:
            return Pasta.objects.filter(paciente_id=paciente_param)

        # fluxo paciente: pega usuário logado
        if hasattr(self.request.user, 'usuario'):
            usuario = self.request.user.usuario
            return Pasta.objects.filter(paciente=usuario)

        # fluxo profissional acessando detalhe sem query param
        return Pasta.objects.all()

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

    def create(self, request, *args, **kwargs):
        # 🔹 Caso o frontend envie uma LISTA de objetos
        if isinstance(request.data, list):
            serializer = self.get_serializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        # 🔹 Caso seja um OBJETO único
        return super().create(request, *args, **kwargs)

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

import time
import logging
from django.db import connection
from django.db.models import Max, F, Prefetch

logger = logging.getLogger(__name__)
class TreinoExecutadoViewSet(viewsets.ModelViewSet):
    serializer_class = TreinoExecutadoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        start = time.time()
        response = super().list(request, *args, **kwargs)
        duration = time.time() - start
        logger.info(f"[VIEW] {request.path} levou {duration:.3f}s")
        return response

    def get_queryset(self):
        user = self.request.user
        queryset = TreinoExecutado.objects.filter(paciente__user=user)

        exercicio_id = self.request.query_params.get("exercicio")
        if exercicio_id:
            exercicios_prefetch = Prefetch(
                "exercicios",
                queryset=ExercicioExecutado.objects.filter(
                    exercicio_id=exercicio_id
                ).prefetch_related("series"),
            )
        else:
            exercicios_prefetch = Prefetch(
                "exercicios",
                queryset=ExercicioExecutado.objects.all().prefetch_related("series"),
            )

        return queryset.prefetch_related(exercicios_prefetch)

    def create(self, request, *args, **kwargs):
        try:
            paciente = Usuário.objects.get(user=request.user)
        except Usuário.DoesNotExist:
            return Response({'error': 'Usuário sem perfil de paciente.'}, status=400)

        payload = request.data.copy()
        payload['paciente'] = paciente.id

        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        treino = self.get_object()

        if not treino.paciente:
            return Response({'error': 'TreinoExecutado sem paciente.'}, status=400)

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
                exercicio_executado = ExercicioExecutado.objects.create(
                    treino_executado=treino,
                    exercicio_id=exercicio_id,
                    rpe=ex_data.get('rpe')
                )
            except Exception as e:
                erros.append(f"Erro ao criar ExercicioExecutado {exercicio_id}: {str(e)}")
                continue

            for s_idx, s in enumerate(ex_data.get('series', [])):
                try:
                    SerieRealizada.objects.create(
                        execucao=exercicio_executado,
                        exercicio=exercicio_executado.exercicio,
                        numero=s.get('numero'),
                        repeticoes=s.get('repeticoes'),
                        carga=s.get('carga')
                    )
                except Exception as e:
                    erros.append(f"Erro na série {s_idx+1} do exercício {exercicio_id}: {str(e)}")

        serializer = self.get_serializer(treino)
        response_data = {'treino': serializer.data}
        if erros:
            response_data['erros'] = erros

        status_code = status.HTTP_200_OK if not erros else status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=status_code)

    # 🔹 Action para evolução detalhada
    @action(detail=False, methods=['get'])
    def evolucao(self, request):
        user = request.user

        queryset = TreinoExecutado.objects.filter(
            paciente__user=user, finalizado=True
        ).prefetch_related(
            Prefetch(
                'exercicios',
                queryset=ExercicioExecutado.objects.prefetch_related('series', 'exercicio__orientacao_detalhes')
            )
        ).order_by('data')

        evolucao = []
        for treino in queryset:
            treino_data = {
                "id": treino.id,
                "data": treino.data,
                "tempo_total": treino.tempo_total,
                "exercicios": []
            }

            for ex in treino.exercicios.all():
                series = ex.series.all()
                treino_data["exercicios"].append({
                    "id": ex.id,
                    "titulo": ex.exercicio.orientacao_detalhes.titulo,
                    "max_repeticoes": max([s.repeticoes for s in series], default=0),
                    "max_carga": max([float(s.carga) for s in series], default=0),
                    "rpe": ex.rpe,
                    "series": [
                        {"numero": s.numero, "repeticoes": s.repeticoes, "carga": s.carga}
                        for s in series
                    ]
                })

            evolucao.append(treino_data)

        return Response(evolucao, status=status.HTTP_200_OK)

    # 🔹 Novo endpoint leve para gráficos
    @action(detail=False, methods=['get'])
    def grafico(self, request):
        user = request.user
        exercicio_id = request.query_params.get("exercicio")

        queryset = TreinoExecutado.objects.filter(paciente__user=user, finalizado=True).prefetch_related(
            Prefetch(
                "exercicios",
                queryset=ExercicioExecutado.objects.filter(exercicio_id=exercicio_id).prefetch_related("series"),
                to_attr="exercicios_filtrados"
            )
        ).order_by("data")

        resultado = []
        for treino in queryset:
            if not treino.exercicios_filtrados:
                continue
            ex = treino.exercicios_filtrados[0]  # assumindo apenas 1 exercício filtrado
            max_reps = max([s.repeticoes for s in ex.series.all()], default=0)
            max_carga = max([float(s.carga) for s in ex.series.all()], default=0)
            rpe = ex.rpe

            resultado.append({
                "id": treino.id,
                "data": treino.data,
                "max_repeticoes": max_reps,
                "max_carga": max_carga,
                "rpe": rpe
            })

        return Response(resultado)
    
class SerieRealizadaViewSet(viewsets.ModelViewSet):
    queryset = SerieRealizada.objects.all().select_related("exercicio", "execucao")
    serializer_class = SerieRealizadaSerializer