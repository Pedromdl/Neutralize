from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, permissions, filters
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework import generics

from orientacoes.paginations import BancoExercicioPagination

# 🔹 Models
from .models import Pasta, Secao, BancodeExercicio, Treino, TreinoExecutado, SerieRealizada, ExercicioExecutado, ExercicioPrescrito
from api.models import Usuário
# 🔹 Serializers
from .serializers import (
    HistoricoTreinoSerializer, PastaSerializer, SecaoSerializer, BancodeExercicioSerializer, TreinoSerializer, TreinoListSerializer, TreinoExecutadoSerializer, SerieRealizadaSerializer,
    ExercicioPrescritoSerializer, TreinoExecutadoAdminSerializer
)
# =========================
# Tela Inicial
# =========================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumo_treinos(request):
    user = request.user
    treinos = TreinoExecutado.objects.filter(paciente__user=user, finalizado=True).order_by('data')

    total = treinos.count()
    ultimo = treinos.last()
    ultimo_data = ultimo.data if ultimo else None

    # cria lista de datas de todos os treinos
    treinos_dias = [t.data.strftime("%d/%m/%Y") for t in treinos]

    return Response({
        "totalTreinosExecutados": total,
        "ultimoTreino": {
            "data": ultimo_data.strftime("%d/%m/%Y") if ultimo else "-"
        },
        "treinosExecutados": treinos_dias
    })
# =========================
# Pastas
# =========================
class PastaViewSet(viewsets.ModelViewSet):
    serializer_class = PastaSerializer

    def get_queryset(self):
        # 🔹 QUERY OTIMIZADA - ELIMINA N+1 COMPLETAMENTE
        queryset = Pasta.objects.all().prefetch_related(
            Prefetch(
                'secoes',
                queryset=Secao.objects.prefetch_related(
                    Prefetch(
                        'treinos',
                        queryset=Treino.objects.prefetch_related(
                            Prefetch(
                                'exercicios',
                                queryset=ExercicioPrescrito.objects.select_related(
                                    'orientacao'
                                ).order_by('id')
                            )
                        ).order_by('id')
                    )
                ).order_by('id')
            )
        )
        
        # 🔹 FILTRO POR PACIENTE
        paciente_param = self.request.query_params.get("paciente")
        if paciente_param:
            queryset = queryset.filter(paciente_id=paciente_param)
        
        # 🔹 FILTRO POR USUÁRIO AUTENTICADO
        elif hasattr(self.request.user, 'usuario'):
            usuario = self.request.user.usuario
            queryset = queryset.filter(paciente=usuario)
        
        else:
            queryset = queryset.none()
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Otimização adicional: contar queries para debug"""
        import time
        from django.db import connection
        
        start_time = time.time()
        connection.queries_log.clear()
        
        response = super().list(request, *args, **kwargs)
        
        duration = time.time() - start_time
        query_count = len(connection.queries)
        
        # Adiciona headers com métricas de performance
        response.headers['X-Query-Count'] = query_count
        response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        return response
# =========================
# Seções
# =========================
class SecaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet otimizado para gerenciar Seções de uma pasta
    Elimina completamente N+1 queries
    """
    serializer_class = SecaoSerializer

    def get_queryset(self):
        # 🔹 QUERY BASE COM PREFETCH
        queryset = Secao.objects.all().prefetch_related(
            Prefetch(
                'treinos',
                queryset=Treino.objects.prefetch_related(
                    Prefetch(
                        'exercicios',
                        queryset=ExercicioPrescrito.objects.select_related('orientacao')
                    )
                ).order_by('id')
            )
        ).select_related('pasta')
        
        # 🔹 FILTROS DINÂMICOS
        pasta_id = self.request.query_params.get('pasta')
        if pasta_id:
            queryset = queryset.filter(pasta_id=pasta_id)
        
        # 🔹 FILTRO POR USUÁRIO (se aplicável)
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'usuario'):
            # Filtra apenas seções cuja pasta pertence ao usuário
            queryset = queryset.filter(pasta__paciente=user.usuario)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Endpoint otimizado para listagem"""
        # 🔹 PAGINAÇÃO OPÇIONAL (se necessário)
        page_size = request.query_params.get('page_size')
        if page_size and page_size.isdigit():
            self.pagination_class.page_size = int(page_size)
        
        return super().list(request, *args, **kwargs)

# =========================
# Orientações
# =========================

class BancodeExercicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar Bancos de Exercício
    """
    queryset = BancodeExercicio.objects.all()
    serializer_class = BancodeExercicioSerializer


    # 🔹 Adiciona Search + Ordering
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # Campos permitidos para ordenação
    ordering_fields = ["id", "titulo"]

    # Ordenação padrão
    ordering = ["titulo"]

    search_fields = ["titulo"]

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
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class TreinoViewSet(viewsets.ModelViewSet):
    queryset = Treino.objects.all()
    serializer_class = TreinoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        secao_id = self.request.query_params.get('secao')
        if secao_id:
            queryset = queryset.filter(secao_id=secao_id)
        return queryset

    @action(detail=False, methods=['get'])
    def por_secao(self, request):
        secao_id = request.query_params.get('secao')
        if not secao_id:
            return Response({"detail": "Parâmetro 'secao' é obrigatório."}, status=400)

        treinos = Treino.objects.filter(secao_id=secao_id)
        serializer = TreinoListSerializer(treinos, many=True)
        return Response(serializer.data)

    # 🔥🔥 NOVA ACTION: DUPLICAR TREINO 🔥🔥
    @action(detail=True, methods=['post'])
    def duplicar(self, request, pk=None):
        treino_original = self.get_object()

        # 1️⃣ Criar novo treino
        novo_treino = Treino.objects.create(
            secao=treino_original.secao,
            nome=f"{treino_original.nome} (cópia)"
        )

        # 2️⃣ Duplicar exercícios associados
        for ex in treino_original.exercicios.all():  # ⚠️ importante: usar related_name correto
            ExercicioPrescrito.objects.create(
                treino=novo_treino,
                orientacao=ex.orientacao,
                series_planejadas=ex.series_planejadas,
                repeticoes_planejadas=ex.repeticoes_planejadas,
                carga_planejada=ex.carga_planejada,
                observacao=ex.observacao
            )

        # 3️⃣ Retorna treino já com exercícios
        serializer = TreinoSerializer(novo_treino)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    
class HistoricoTreinoList(generics.ListAPIView):
    serializer_class = HistoricoTreinoSerializer

    def get_queryset(self):
        try:
            usuario = Usuário.objects.get(user=self.request.user)
        except Usuário.DoesNotExist:
            return TreinoExecutado.objects.none()   # ⬅ evita erro e retorna vazio

        return (
            TreinoExecutado.objects.filter(paciente=usuario)
            .select_related("treino")
            .order_by("-data")
        )


import time
import logging
from django.db import connection
from django.db.models import Max, F, Prefetch, Avg, Count, Q

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
        return TreinoExecutado.objects.select_related(
            'paciente',
            'paciente__user',
            'treino'
        ).prefetch_related(
            Prefetch(
                'exercicios',
                queryset=ExercicioExecutado.objects.select_related(
                    'exercicio__orientacao'
                ).prefetch_related('series')
            )
        ).annotate(
            paciente_nome=Concat(
                F('paciente__user__first_name'),
                Value(' '),
                F('paciente__user__last_name'),
                output_field=CharField()
            ),
            treino_nome=F('treino__nome')
        ).order_by('-data', '-id')
    
    def create(self, request, *args, **kwargs):
        try:
            paciente = Usuário.objects.get(user=request.user)
        except Usuário.DoesNotExist:
            return Response({'error': 'Usuário sem perfil de paciente.'}, status=400)

        payload = request.data.copy()
        payload['paciente'] = paciente.id  # backend preenche paciente
        treino_id = payload.get("treino")

        if not treino_id:
            return Response({'error': 'ID do treino não foi enviado.'}, status=400)

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
                # 🔹 Agora salva só no ExercicioExecutado
                ExercicioExecutado.objects.create(
                    treino_executado=treino,
                    exercicio_id=exercicio_id,
                    rpe=ex_data.get('rpe'),
                    seriess=ex_data.get('series', [])  # fica tudo no JSONField
                )
            except Exception as e:
                erros.append(f"Erro ao criar ExercicioExecutado {exercicio_id}: {str(e)}")
                continue

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

from api.mixins import OrganizacaoFilterMixin
from rest_framework.pagination import PageNumberPagination


from api.mixins import OrganizacaoFilterMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response

class TreinoExecutadoPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat

class TreinoExecutadoAdminViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    """T
    ViewSet administrativo OTIMIZADO - zero queries N+1
    """
    serializer_class = TreinoExecutadoAdminSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TreinoExecutadoPagination
    queryset = TreinoExecutado.objects.all()
    organizacao_field = "paciente__organizacao"

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 🔹 FILTRO POR BUSCA (search) - CORRIGIDO
        search_query = self.request.query_params.get('search', None)
        if search_query:
            # Remover espaços extras e dividir em termos
            search_terms = search_query.strip().split()
            
            # Criar query dinâmica para cada termo
            query = Q()
            for term in search_terms:
                query &= (
                    Q(paciente__user__first_name__icontains=term) |
                    Q(paciente__user__last_name__icontains=term) |
                    Q(treino__nome__icontains=term)
                )
            
            queryset = queryset.filter(query)

        # 🔹 QUERY OTIMIZADA COM ANNOTATE
        queryset = queryset.select_related(
            'paciente',
            'paciente__user',
            'treino'
        ).prefetch_related(
            Prefetch(
                'exercicios',
                queryset=ExercicioExecutado.objects.select_related(
                    'exercicio',
                    'exercicio__orientacao'
                ).prefetch_related('series')
            )
        ).annotate(
            paciente_nome=Concat(
                F('paciente__user__first_name'),
                Value(' '),
                F('paciente__user__last_name'),
                output_field=CharField()
            ),
            treino_nome=F('treino__nome')
        ).order_by('-data', '-id')

        return queryset

    def list(self, request, *args, **kwargs):
        start = time.time()
        response = super().list(request, *args, **kwargs)
        duration = time.time() - start
        logger.info(f"[ADMIN VIEW OTIMIZADO] {request.path} levou {duration:.3f}s")
        return response