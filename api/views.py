from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Max, OuterRef, Subquery
from datetime import timedelta
import calendar
from .models import (
    Usuário, ForcaMuscular, Mobilidade, CategoriaTeste, TodosTestes, TesteFuncao, TesteDor, PreAvaliacao, Anamnese, Pasta, Secao, Orientacao,
    Evento, Sessao
)
from .serializers import (
    UsuárioSerializer, ForcaMuscularSerializer, MobilidadeSerializer,
    CategoriaTesteSerializer, TodosTestesSerializer, TesteFuncaoSerializer, TesteDorSerializer, PreAvaliacaoSerializer, AnamneseSerializer,
    PastaSerializer, SecaoSerializer, OrientacaoSerializer, EventoSerializer, SessaoSerializer
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
            movimento_forca=OuterRef('movimento_forca')
        ).order_by('-data_avaliacao').values('data_avaliacao')[:1]

        return ForcaMuscular.objects.filter(
            paciente_id=paciente_id,
            data_avaliacao=Subquery(latest_date_subquery)
        ).order_by('movimento_forca')

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

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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

class PreAvaliacaoViewSet(viewsets.ModelViewSet):
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

class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['paciente']  # permite filtro por paciente

    def create(self, request, *args, **kwargs):
        dados = request.data
        repetir = dados.get("repetir", False)
        frequencia = dados.get("frequencia", "nenhuma")
        repeticoes = int(dados.get("repeticoes") or 0)

        # Criação do evento principal
        serializer = self.get_serializer(data=dados)
        serializer.is_valid(raise_exception=True)
        evento_principal = serializer.save()

        # Gerar eventos futuros, se necessário
        if repetir and frequencia != "nenhuma" and repeticoes > 0:
            data_base = evento_principal.data
            for i in range(1, repeticoes):
                nova_data = self.calcular_proxima_data(data_base, frequencia, i)
                novo_evento = Evento.objects.create(
                    paciente=evento_principal.paciente,
                    tipo=evento_principal.tipo,
                    status=evento_principal.status,
                    data=nova_data,
                    hora_inicio=evento_principal.hora_inicio,
                    hora_fim=evento_principal.hora_fim,
                    responsavel=evento_principal.responsavel,
                    repetir=False,
                    frequencia="nenhuma",
                    evento_pai=evento_principal
                )

        return Response(EventoSerializer(evento_principal).data, status=status.HTTP_201_CREATED)

    def calcular_proxima_data(self, data_inicial, frequencia, i):
        if frequencia == "diario":
            return data_inicial + timedelta(days=i)
        elif frequencia == "semanal":
            return data_inicial + timedelta(weeks=i)
        elif frequencia == "mensal":
            # Ajuste simples para meses futuros
            mes = data_inicial.month - 1 + i
            ano = data_inicial.year + mes // 12
            mes = mes % 12 + 1
            dia = min(data_inicial.day, calendar.monthrange(ano, mes)[1])
            return data_inicial.replace(year=ano, month=mes, day=dia)
        return data_inicial
    
class SessaoViewSet(viewsets.ModelViewSet):
    queryset = Sessao.objects.all()
    serializer_class = SessaoSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get("paciente")
        if paciente_id:
            return Sessao.objects.filter(paciente_id=paciente_id)
        return Sessao.objects.all()  # Retorna tudo se não filtrar