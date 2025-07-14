from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Max, OuterRef, Subquery
from .models import Usuário, ForcaMuscular, Mobilidade, CategoriaTeste, TodosTestes, TesteFuncao, TesteDor, PreAvaliacao, Anamnese, Pasta, Secao, Orientacao
from .serializers import (
    UsuárioSerializer, ForcaMuscularSerializer, MobilidadeSerializer,
    CategoriaTesteSerializer, TodosTestesSerializer, TesteFuncaoSerializer, TesteDorSerializer, PreAvaliacaoSerializer, AnamneseSerializer, 
    PastaSerializer, SecaoSerializer, OrientacaoSerializer
)
from rest_framework.response import Response
from rest_framework import status



class UsuárioViewSet(viewsets.ModelViewSet):
    queryset = Usuário.objects.all()
    serializer_class = UsuárioSerializer

class ForcaMuscularViewSet(viewsets.ModelViewSet):
    queryset = ForcaMuscular.objects.all()
    serializer_class = ForcaMuscularSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        data = self.request.query_params.get('data_avaliacao')

        if not paciente_id:
            return ForcaMuscular.objects.none()

        if data:
            return ForcaMuscular.objects.filter(paciente_id=paciente_id, data_avaliacao=data)

        latest_date_subquery = ForcaMuscular.objects.filter(
            paciente_id=paciente_id,
            musculatura=OuterRef('musculatura')
        ).order_by('-data_avaliacao').values('data_avaliacao')[:1]

        return ForcaMuscular.objects.filter(
            paciente_id=paciente_id,
            data_avaliacao=Subquery(latest_date_subquery)
        ).order_by('musculatura')

    @action(detail=False, methods=["get"])
    def datas(self, request):
        paciente_id = request.query_params.get('paciente')
        if not paciente_id:
            return Response([], status=400)

        datas = (
            ForcaMuscular.objects.filter(paciente_id=paciente_id)
            .values_list('data_avaliacao', flat=True)
            .distinct()
            .order_by('-data_avaliacao')
        )
        return Response(datas)



class MobilidadeViewSet(viewsets.ModelViewSet):
    queryset = Mobilidade.objects.all()
    serializer_class = MobilidadeSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        data = self.request.query_params.get('data_avaliacao')  # nova linha

        if not paciente_id:
            return Mobilidade.objects.none()

        if data:
            return Mobilidade.objects.filter(
                paciente_id=paciente_id,
                data_avaliacao=data
            ).order_by('nome')

        latest_date_subquery = Mobilidade.objects.filter(
            paciente_id=paciente_id,
            nome=OuterRef('nome')
        ).order_by('-data_avaliacao').values('data_avaliacao')[:1]

        return Mobilidade.objects.filter(
            paciente_id=paciente_id,
            data_avaliacao=Subquery(latest_date_subquery)
        ).order_by('nome')
    
    @action(detail=False, methods=["get"])
    def datas(self, request):
        paciente_id = request.query_params.get('paciente')
        if not paciente_id:
            return Response([], status=400)

        datas = (
            Mobilidade.objects.filter(paciente_id=paciente_id)
            .values_list('data_avaliacao', flat=True)
            .distinct()
            .order_by('-data_avaliacao')
        )
        return Response(datas)



class CategoriaTesteViewSet(viewsets.ModelViewSet):
    queryset = CategoriaTeste.objects.all()
    serializer_class = CategoriaTesteSerializer


class TodosTestesViewSet(viewsets.ModelViewSet):
    serializer_class = TodosTestesSerializer

    def get_queryset(self):
        categoria = self.request.query_params.get('categoria')  # ex: ?categoria=Testes de Dor
        queryset = TodosTestes.objects.all()

        if categoria:
            queryset = queryset.filter(categoria__nome__iexact=categoria)

        return queryset


class TesteFuncaoViewSet(viewsets.ModelViewSet):
    queryset = TesteFuncao.objects.all()
    serializer_class = TesteFuncaoSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        data = self.request.query_params.get('data_avaliacao')  # filtro de data recebido

        if not paciente_id:
            return TesteFuncao.objects.none()

        queryset = TesteFuncao.objects.filter(paciente_id=paciente_id)

        if data:
            # Se data informada, filtra somente essa data
            return queryset.filter(data_avaliacao=data)

        # Se data não informada, retorna os registros mais recentes por teste
        latest_dates = (
            queryset
            .values('teste_id')
            .annotate(max_date=Max('data_avaliacao'))
        )

        qs = TesteFuncao.objects.none()
        for ld in latest_dates:
            qs |= queryset.filter(
                teste_id=ld['teste_id'],
                data_avaliacao=ld['max_date']
            )

        return qs

    @action(detail=False, methods=["get"])
    def datas(self, request):
        paciente_id = request.query_params.get('paciente')
        if not paciente_id:
            return Response([], status=400)

        datas = (
            TesteFuncao.objects.filter(paciente_id=paciente_id)
            .values_list('data_avaliacao', flat=True)
            .distinct()
            .order_by('-data_avaliacao')
        )
        return Response(datas)



class TesteDorViewSet(viewsets.ModelViewSet):
    queryset = TesteDor.objects.all()
    serializer_class = TesteDorSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        data = self.request.query_params.get('data_avaliacao')  # filtro de data recebido

        if not paciente_id:
            return TesteDor.objects.none()

        queryset = TesteDor.objects.filter(paciente_id=paciente_id)

        if data:
            # Se data informada, filtra somente essa data
            return queryset.filter(data_avaliacao=data)

        # Se data não informada, retorna os registros mais recentes por teste
        latest_dates = (
            queryset
            .values('teste_id')
            .annotate(max_date=Max('data_avaliacao'))
        )

        qs = TesteDor.objects.none()
        for ld in latest_dates:
            qs |= queryset.filter(
                teste_id=ld['teste_id'],
                data_avaliacao=ld['max_date']
            )

        return qs

    @action(detail=False, methods=["get"])
    def datas(self, request):
        paciente_id = request.query_params.get('paciente')
        if not paciente_id:
            return Response([], status=400)

        datas = (
            TesteDor.objects.filter(paciente_id=paciente_id)
            .values_list('data_avaliacao', flat=True)
            .distinct()
            .order_by('-data_avaliacao')
        )
        return Response(datas)

class DatasDisponiveisAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        paciente_id = request.query_params.get('paciente')
        if not paciente_id:
            return Response({'erro': 'ID do paciente não informado'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Pega todas as datas dos modelos, como datetime ou date
            forca_datas = ForcaMuscular.objects.filter(paciente_id=paciente_id).values_list('data_avaliacao', flat=True)
            mobilidade_datas = Mobilidade.objects.filter(paciente_id=paciente_id).values_list('data_avaliacao', flat=True)
            funcao_datas = TesteFuncao.objects.filter(paciente_id=paciente_id).values_list('data_avaliacao', flat=True)
            dor_datas = TesteDor.objects.filter(paciente_id=paciente_id).values_list('data_avaliacao', flat=True)

            # Função para extrair a data (se for datetime pega só a parte date)
            def extrair_data(dt):
                if dt is None:
                    return None
                if hasattr(dt, 'date'):
                    return dt.date()
                return dt

            # Aplica extrair_data para cada lista e transforma em conjunto (para datas únicas)
            forca_datas_set = set(filter(None, (extrair_data(dt) for dt in forca_datas)))
            mobilidade_datas_set = set(filter(None, (extrair_data(dt) for dt in mobilidade_datas)))
            funcao_datas_set = set(filter(None, (extrair_data(dt) for dt in funcao_datas)))
            dor_datas_set = set(filter(None, (extrair_data(dt) for dt in dor_datas)))

            # Junta todas as datas e ordena decrescente
            todas_datas = sorted(
                forca_datas_set | mobilidade_datas_set | funcao_datas_set | dor_datas_set,
                reverse=True
            )

            # Converte para string ISO (ex: '2025-07-11')
            todas_datas_str = [data.isoformat() for data in todas_datas]

            return Response(todas_datas_str)

        except Exception as e:
            return Response({'erro': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PreAvaliacaoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PreAvaliacao.objects.all()
    serializer_class = PreAvaliacaoSerializer

class AnamneseViewSet(viewsets.ModelViewSet):
    queryset = Anamnese.objects.all()
    serializer_class = AnamneseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['paciente']  # <- permite filtrar por ?paciente=ID

class PastaViewSet(viewsets.ModelViewSet):
    serializer_class = PastaSerializer
    queryset = Pasta.objects.all()  # 👈 isso é necessário para DRF funcionar corretamente

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        if paciente_id:
            return Pasta.objects.filter(paciente__id=paciente_id)
        return self.queryset

class SecaoViewSet(viewsets.ModelViewSet):
    queryset = Secao.objects.all()
    serializer_class = SecaoSerializer

class OrientacaoViewSet(viewsets.ModelViewSet):
    queryset = Orientacao.objects.all()
    serializer_class = OrientacaoSerializer

from html2docx import html2docx
from django.http import HttpResponse
import re
from .models import Anamnese

def remover_cor_html(html):
    html = re.sub(r'style="[^"]*color\s*:\s*[^;"]+;?[^"]*"', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<font[^>]*color="[^"]*"[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</font>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'style="\s*"', '', html)
    return html

def exportar_avaliacao_docx(request, pk):
    avaliacao = Anamnese.objects.get(pk=pk)
    titulo = f"Avaliação - {avaliacao.paciente.nome}"

    html_limpo = remover_cor_html(avaliacao.conteudo_html)
    docx_io = html2docx(html_limpo, title=titulo)  # Retorna BytesIO direto

    docx_io.seek(0)

    response = HttpResponse(
        docx_io.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{titulo}.docx"'

    return response
