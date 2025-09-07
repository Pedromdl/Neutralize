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
    ExercicioPrescritoSerializer, TreinoExecutadoCreateSerializer
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

class TreinoExecutadoViewSet(viewsets.ModelViewSet):
    serializer_class = TreinoExecutadoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user  # 🔹 CustomUser
        return TreinoExecutado.objects.filter(paciente__user=user)

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
                exercicio_executado = ExercicioExecutado.objects.create(
                    treino_executado=treino,
                    exercicio_id=exercicio_id,
                    rpe=ex_data.get('rpe')
                )
            except Exception as e:
                erros.append(f"Erro ao criar ExercicioExecutado {exercicio_id}: {str(e)}")
                continue

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