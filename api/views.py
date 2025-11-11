# ========================
# IMPORTAÇÕES PADRÃO / PYTHON
# ========================
import os
import re
import base64
import calendar
from io import BytesIO
from datetime import date, timedelta

# ========================
# IMPORTAÇÕES TERCEIROS (MATPLOTLIB ANTES DE TUDO)
# ========================
import matplotlib
matplotlib.use('Agg')  # backend não interativo, deve ser chamado antes de pyplot
import matplotlib.pyplot as plt

# Outros terceiros
from html2docx import html2docx
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

# ========================
# IMPORTAÇÕES DJANGO
# ========================
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Max, OuterRef, Subquery

# ========================
# IMPORTAÇÕES LOCAIS (MODELS & SERIALIZERS)
# ========================
from .permissions import IsProfissional, IsPaciente
from .models import (
    RelatorioPublico, Usuário, Estabilidade, ForcaMuscular, Mobilidade, 
    CategoriaTeste, TodosTestes, TesteFuncao, TesteDor, PreAvaliacao, 
    Anamnese, Evento, Sessao
)
from .serializers import (
    UsuárioSerializer, EstabilidadeSerializer, ForcaMuscularSerializer, MobilidadeSerializer,
    CategoriaTesteSerializer, TodosTestesSerializer, TesteFuncaoSerializer, TesteDorSerializer, 
    PreAvaliacaoSerializer, AnamneseSerializer, EventoSerializer, SessaoSerializer
)


class UsuárioViewSet(viewsets.ModelViewSet):
    queryset = Usuário.objects.all()
    serializer_class = UsuárioSerializer
    permission_classes = [IsAuthenticated, IsProfissional]  # apenas profissionais podem acessar

class ForcaMuscularViewSet(viewsets.ModelViewSet):
    queryset = ForcaMuscular.objects.all()
    serializer_class = ForcaMuscularSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        data = self.request.query_params.get('data_avaliacao')

        if not paciente_id:
            return ForcaMuscular.objects.none()

        # 🔹 Filtra por data específica e ordena por id
        if data:
            return ForcaMuscular.objects.filter(
                paciente_id=paciente_id, 
                data_avaliacao=data
            ).order_by('id')

        # 🔹 Caso contrário, traz o último registro de cada movimento
        latest_date_subquery = ForcaMuscular.objects.filter(
            paciente_id=paciente_id,
            movimento_forca=OuterRef('movimento_forca')
        ).order_by('-data_avaliacao').values('data_avaliacao')[:1]

        return ForcaMuscular.objects.filter(
            paciente_id=paciente_id,
            data_avaliacao=Subquery(latest_date_subquery)
        ).order_by('id')  # 🔹 ordenação por id para consistência

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
        data = self.request.query_params.get('data_avaliacao')

        if not paciente_id:
            return Mobilidade.objects.none()

        # 🔹 Se existe data específica, filtra e ordena por id
        if data:
            return Mobilidade.objects.filter(
                paciente_id=paciente_id,
                data_avaliacao=data
            ).order_by('id')

        # 🔹 Caso contrário, traz o último registro de cada movimento
        latest_date_subquery = Mobilidade.objects.filter(
            paciente_id=paciente_id,
            nome=OuterRef('nome')
        ).order_by('-data_avaliacao').values('data_avaliacao')[:1]

        return Mobilidade.objects.filter(
            paciente_id=paciente_id,
            data_avaliacao=Subquery(latest_date_subquery)
        ).order_by('id')  # 🔹 ordenação por id para consistência

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

class EstabilidadeViewSet(viewsets.ModelViewSet):
    queryset = Estabilidade.objects.all()
    serializer_class = EstabilidadeSerializer

    def get_queryset(self):
        paciente_id = self.request.query_params.get('paciente')
        data = self.request.query_params.get('data_avaliacao')

        if not paciente_id:
            return Estabilidade.objects.none()

        # 🔹 Filtra por data específica, se fornecida
        if data:
            return Estabilidade.objects.filter(
                paciente_id=paciente_id,
                data_avaliacao=data
            ).order_by('id')  # ordena por id

        # 🔹 Última avaliação por movimento
        latest_date_subquery = Estabilidade.objects.filter(
            paciente_id=paciente_id,
            movimento_estabilidade=OuterRef('movimento_estabilidade')
        ).order_by('-data_avaliacao').values('data_avaliacao')[:1]

        return Estabilidade.objects.filter(
            paciente_id=paciente_id,
            data_avaliacao=Subquery(latest_date_subquery)
        ).order_by('id')  # ordena por id

    @action(detail=False, methods=["get"])
    def datas(self, request):
        paciente_id = request.query_params.get('paciente')
        if not paciente_id:
            return Response([], status=400)

        datas = (
            Estabilidade.objects.filter(paciente_id=paciente_id)
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

        # Evento principal
        serializer = self.get_serializer(data=dados)
        serializer.is_valid(raise_exception=True)
        evento_principal = serializer.save()

        eventos_criados = [evento_principal]

        # Eventos repetidos
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
                eventos_criados.append(novo_evento)

        return Response(
            EventoSerializer(eventos_criados, many=True).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # evento principal
        dados = request.data

        repetir = dados.get("repetir", False)
        frequencia = dados.get("frequencia", "nenhuma")
        repeticoes = int(dados.get("repeticoes") or 0)

        # Atualiza o evento principal
        serializer = self.get_serializer(instance, data=dados, partial=partial)
        serializer.is_valid(raise_exception=True)
        evento_atualizado = serializer.save()

        # Remove as ocorrências antigas vinculadas
        evento_atualizado.ocorrencias.all().delete()

        # Se precisa criar novas recorrências
        if repetir and frequencia != "nenhuma" and repeticoes > 0:
            data_base = evento_atualizado.data
            for i in range(1, repeticoes):
                nova_data = self.calcular_proxima_data(data_base, frequencia, i)
                Evento.objects.create(
                    paciente=evento_atualizado.paciente,
                    tipo=evento_atualizado.tipo,
                    status=evento_atualizado.status,
                    data=nova_data,
                    hora_inicio=evento_atualizado.hora_inicio,
                    hora_fim=evento_atualizado.hora_fim,
                    responsavel=evento_atualizado.responsavel,
                    repetir=False,
                    frequencia="nenhuma",
                    evento_pai=evento_atualizado
                )

        return Response(self.get_serializer(evento_atualizado).data, status=status.HTTP_200_OK)

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
    
from django.template.loader import render_to_string
from django.http import HttpResponse
import os
from django.conf import settings
import pdfkit
import base64

def gerar_relatorio_pdf(request, paciente_id):
    paciente = Usuário.objects.get(id=paciente_id)

    # Pega a data selecionada enviada pelo React (query param)
    data_selecionada = request.GET.get('data')  # ex: '2025-11-09'

    # Caminho absoluto da logo
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logoletrapreta.png")

    # Converte a logo em base64
    try:
        with open(logo_path, "rb") as img_file:
            logo_base64 = base64.b64encode(img_file.read()).decode("utf-8")
    except FileNotFoundError:
        logo_base64 = ""  # Evita erro se a imagem não existir

    idade = calcular_idade(paciente.data_de_nascimento)

    # ✅ Chama as funções de gráfico, passando a data selecionada
    grafico_forca_base64 = gerar_grafico_forca_muscular(paciente, data_selecionada)
    grafico_mobilidade_base64 = gerar_grafico_mobilidade(paciente, data_selecionada)
    grafico_estabilidade_base64 = gerar_grafico_estabilidade(paciente, data_selecionada)
    grafico_dor_base64 = gerar_grafico_dor(paciente, data_selecionada)
    grafico_funcao_base64 = gerar_grafico_funcao(paciente, data_selecionada)

    # Renderiza o HTML com o logo, dados do paciente e gráficos
    html_string = render_to_string("relatorio.html", {
        "logo_base64": logo_base64,
        "nome": paciente.nome,
        "cpf": paciente.cpf,
        "email": paciente.email,
        "telefone": paciente.telefone,
        "endereço": paciente.endereço,
        "data_de_nascimento": paciente.data_de_nascimento,
        "idade": idade,
        "grafico_forca": grafico_forca_base64,
        "grafico_mobilidade": grafico_mobilidade_base64,
        "grafico_estabilidade": grafico_estabilidade_base64,
        "grafico_dor": grafico_dor_base64,
        "grafico_funcao": grafico_funcao_base64,
    })

    # Caminho do executável wkhtmltopdf
    config = pdfkit.configuration(
        wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    )

    # Gera o PDF com fundo e margens ajustadas
    pdf_bytes = pdfkit.from_string(
        html_string,
        False,
        configuration=config,
        options={
            'page-size': 'A4',
            'margin-top': '0mm',
            'margin-right': '0mm',
            'margin-bottom': '0mm',
            'margin-left': '0mm',
            'encoding': "UTF-8",
            'print-media-type': '',
            'background': '',
            'disable-smart-shrinking': '',
        }
    )

    # Retorna o PDF como download
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="relatorio_{paciente.nome}.pdf"'
    return response


def calcular_idade(data_nascimento):
    if not data_nascimento:
        return None
    hoje = date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )

def gerar_grafico_forca_muscular(paciente, data_selecionada=None):

    print(f"[DEBUG] gerando gráfico para paciente: {paciente.nome}")
    print(f"[DEBUG] data_selecionada: {data_selecionada}")

    # Filtra os registros do paciente
    qs = ForcaMuscular.objects.filter(paciente=paciente)
    print(f"[DEBUG] total de registros do paciente: {qs.count()}")

    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)
        print(f"[DEBUG] registros após filtro de data: {qs.count()}")

    # Busca os últimos registros por movimento
    ultimas_avaliacoes = (
        qs
        .values("movimento_forca__nome")
        .annotate(data_mais_recente=Max("data_avaliacao"))
    )
    print(f"[DEBUG] ultimas_avaliacoes: {list(ultimas_avaliacoes)}")

    # Rebusca os objetos correspondentes
    dados = []
    for item in ultimas_avaliacoes:
        registro = (
            qs
            .filter(
                movimento_forca__nome=item["movimento_forca__nome"],
                data_avaliacao=item["data_mais_recente"]
            )
            .first()
        )
        if registro:
            dados.append(registro)
    print(f"[DEBUG] quantidade de dados usados no gráfico: {len(dados)}")

    if not dados:
        print("[DEBUG] Nenhum dado encontrado para gerar o gráfico")
        return None

    # Prepara os dados
    movimentos = [d.movimento_forca.nome if d.movimento_forca else "Movimento" for d in dados]
    lado_esquerdo = [float(d.lado_esquerdo) for d in dados]
    lado_direito = [float(d.lado_direito) for d in dados]

    # Criação do gráfico
    plt.figure(figsize=(4.2, 3))
    x = range(len(movimentos))
    largura = 0.45

    barras_esq = plt.bar(
        [i - largura / 2 for i in x], lado_esquerdo,
        width=largura, label="Lado Esquerdo", color="#b7de42"
    )
    barras_dir = plt.bar(
        [i + largura / 2 for i in x], lado_direito,
        width=largura, label="Lado Direito", color="#282829"
    )

    # Valores dentro das barras
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{altura:g}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if barra.get_facecolor() == (0.16, 0.16, 0.16, 1) else "black",
            )

    # Configurações de eixo e legenda
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=8)

    plt.xticks(x, movimentos, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Força (Kg)", fontsize=8)
    plt.title("Avaliação de Força Muscular", fontsize=9)
    plt.legend(fontsize=7)
    plt.tight_layout()

    # Converte em base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return image_base64

def gerar_grafico_mobilidade(paciente, data_selecionada=None):

    print(f"[DEBUG] gerando gráfico de mobilidade para paciente: {paciente.nome}")
    print(f"[DEBUG] data_selecionada: {data_selecionada}")

    # Filtra os registros do paciente
    qs = Mobilidade.objects.filter(paciente=paciente)
    print(f"[DEBUG] total de registros do paciente: {qs.count()}")

    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)
        print(f"[DEBUG] registros após filtro de data: {qs.count()}")

    # Busca os últimos registros por teste de mobilidade
    ultimas_avaliacoes = (
        qs
        .values("nome__nome")
        .annotate(data_mais_recente=Max("data_avaliacao"))
    )
    print(f"[DEBUG] ultimas_avaliacoes: {list(ultimas_avaliacoes)}")

    # Rebusca os objetos correspondentes
    dados = []
    for item in ultimas_avaliacoes:
        registro = (
            qs
            .filter(
                nome__nome=item["nome__nome"],
                data_avaliacao=item["data_mais_recente"]
            )
            .first()
        )
        if registro:
            dados.append(registro)
    print(f"[DEBUG] quantidade de dados usados no gráfico: {len(dados)}")

    if not dados:
        print("[DEBUG] Nenhum dado encontrado para gerar o gráfico")
        return None

    # Prepara os dados
    testes = [d.nome.nome if d.nome else "Teste" for d in dados]
    lado_esquerdo = [float(d.lado_esquerdo) for d in dados]
    lado_direito = [float(d.lado_direito) for d in dados]

    # Criação do gráfico
    plt.figure(figsize=(4.2, 3))
    x = range(len(testes))
    largura = 0.45

    barras_esq = plt.bar(
        [i - largura / 2 for i in x], lado_esquerdo,
        width=largura, label="Lado Esquerdo", color="#b7de42"
    )
    barras_dir = plt.bar(
        [i + largura / 2 for i in x], lado_direito,
        width=largura, label="Lado Direito", color="#282829"
    )

    # Valores dentro das barras
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{int(altura)}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if barra.get_facecolor() == (0.16, 0.16, 0.16, 1) else "black",
            )

    # Configurações de eixo e legenda
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=6)

    plt.xticks(x, testes, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Amplitude (°)", fontsize=8)
    plt.title("Avaliação de Mobilidade", fontsize=9)
    plt.legend(fontsize=7)
    plt.tight_layout()

    # Converte para base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return image_base64

def gerar_grafico_estabilidade(paciente, data_selecionada=None):
    print(f"[DEBUG] gerando gráfico de estabilidade para paciente: {paciente.nome}")
    print(f"[DEBUG] data_selecionada: {data_selecionada}")

    # Filtra os registros do paciente
    qs = Estabilidade.objects.filter(paciente=paciente)
    print(f"[DEBUG] total de registros do paciente: {qs.count()}")

    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)
        print(f"[DEBUG] registros após filtro de data: {qs.count()}")

    # Busca os últimos registros por movimento
    ultimas_avaliacoes = (
        qs
        .values("movimento_estabilidade__nome")
        .annotate(data_mais_recente=Max("data_avaliacao"))
    )
    print(f"[DEBUG] ultimas_avaliacoes: {list(ultimas_avaliacoes)}")

    # Rebusca os objetos correspondentes
    dados = []
    for item in ultimas_avaliacoes:
        registro = (
            qs
            .filter(
                movimento_estabilidade__nome=item["movimento_estabilidade__nome"],
                data_avaliacao=item["data_mais_recente"]
            )
            .first()
        )
        if registro:
            dados.append(registro)
    print(f"[DEBUG] quantidade de dados usados no gráfico: {len(dados)}")

    if not dados:
        print("[DEBUG] Nenhum dado encontrado para gerar o gráfico de estabilidade")
        return None

    # Prepara os dados
    movimentos = [d.movimento_estabilidade.nome if d.movimento_estabilidade else "Movimento" for d in dados]
    lado_esquerdo = []
    lado_direito = []

    for d in dados:
        try:
            lado_esquerdo.append(float(d.lado_esquerdo))
            lado_direito.append(float(d.lado_direito))
        except ValueError:
            lado_esquerdo.append(0)
            lado_direito.append(0)

    # Criação do gráfico
    plt.figure(figsize=(4.2, 3))
    x = range(len(movimentos))
    largura = 0.45

    barras_esq = plt.bar(
        [i - largura / 2 for i in x], lado_esquerdo,
        width=largura, label="Lado Esquerdo", color="#b7de42"
    )
    barras_dir = plt.bar(
        [i + largura / 2 for i in x], lado_direito,
        width=largura, label="Lado Direito", color="#282829"
    )

    # Valores dentro das barras
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{altura:g}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if barra.get_facecolor() == (0.16, 0.16, 0.16, 1) else "black",
            )

    # Configurações de eixo e legenda
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=8)

    plt.xticks(x, movimentos, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Pontuação / Tempo", fontsize=8)
    plt.title("Avaliação de Estabilidade", fontsize=9)
    plt.legend(fontsize=7)
    plt.tight_layout()

    # Converte em base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return image_base64

def gerar_grafico_funcao(paciente, data_selecionada=None):
    print(f"[DEBUG] gerando gráfico de função para paciente: {paciente.nome}")
    print(f"[DEBUG] data_selecionada: {data_selecionada}")

    # Filtra os registros do paciente
    qs = TesteFuncao.objects.filter(paciente=paciente)
    print(f"[DEBUG] total de registros do paciente: {qs.count()}")

    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)
        print(f"[DEBUG] registros após filtro de data: {qs.count()}")

    # Busca as últimas avaliações de cada teste
    ultimas_avaliacoes = (
        qs
        .values("teste__nome")
        .annotate(data_mais_recente=Max("data_avaliacao"))
    )
    print(f"[DEBUG] ultimas_avaliacoes: {list(ultimas_avaliacoes)}")

    # Rebusca os objetos correspondentes
    dados = []
    for item in ultimas_avaliacoes:
        registro = (
            qs
            .filter(
                teste__nome=item["teste__nome"],
                data_avaliacao=item["data_mais_recente"]
            )
            .first()
        )
        if registro:
            dados.append(registro)

    print(f"[DEBUG] quantidade de dados usados no gráfico: {len(dados)}")

    if not dados:
        print("[DEBUG] Nenhum dado encontrado para gerar o gráfico de função")
        return None

    # Prepara os dados para o gráfico
    testes = [d.teste.nome if d.teste else "Teste" for d in dados]
    lado_esquerdo = []
    lado_direito = []

    for d in dados:
        try:
            lado_esquerdo.append(float(d.lado_esquerdo))
            lado_direito.append(float(d.lado_direito))
        except ValueError:
            lado_esquerdo.append(0)
            lado_direito.append(0)

    # Criação do gráfico
    plt.figure(figsize=(4.2, 3))
    x = range(len(testes))
    largura = 0.45

    barras_esq = plt.bar(
        [i - largura / 2 for i in x], lado_esquerdo,
        width=largura, label="Lado Esquerdo", color="#b7de42"
    )
    barras_dir = plt.bar(
        [i + largura / 2 for i in x], lado_direito,
        width=largura, label="Lado Direito", color="#282829"
    )

    # Valores dentro das barras
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{altura:g}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if barra.get_facecolor() == (0.16, 0.16, 0.16, 1) else "black",
            )

    # Aparência e legendas
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=8)

    plt.xticks(x, testes, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Pontuação / Tempo", fontsize=8)
    plt.title("Testes de Função", fontsize=9)
    plt.legend(fontsize=7)
    plt.tight_layout()

    # Converte para Base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return image_base64

def gerar_grafico_dor(paciente, data_selecionada=None):
    print(f"[DEBUG] gerando gráfico de dor para paciente: {paciente.nome}")
    print(f"[DEBUG] data_selecionada: {data_selecionada}")

    # Filtra os registros do paciente
    qs = TesteDor.objects.filter(paciente=paciente)
    print(f"[DEBUG] total de registros do paciente: {qs.count()}")

    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)
        print(f"[DEBUG] registros após filtro de data: {qs.count()}")

    # Busca as últimas avaliações de cada teste
    ultimas_avaliacoes = (
        qs
        .values("teste__nome")
        .annotate(data_mais_recente=Max("data_avaliacao"))
    )
    print(f"[DEBUG] ultimas_avaliacoes: {list(ultimas_avaliacoes)}")

    # Rebusca os objetos correspondentes
    dados = []
    for item in ultimas_avaliacoes:
        registro = (
            qs
            .filter(
                teste__nome=item["teste__nome"],
                data_avaliacao=item["data_mais_recente"]
            )
            .first()
        )
        if registro:
            dados.append(registro)

    print(f"[DEBUG] quantidade de dados usados no gráfico: {len(dados)}")

    if not dados:
        print("[DEBUG] Nenhum dado encontrado para gerar o gráfico de dor")
        return None

    # Prepara os dados
    testes = [d.teste.nome if d.teste else "Teste" for d in dados]
    resultados = []

    for d in dados:
        try:
            resultados.append(float(d.resultado))
        except ValueError:
            resultados.append(0)

    # Criação do gráfico
    plt.figure(figsize=(4.2, 3))
    x = range(len(testes))

    barras = plt.bar(x, resultados, color="#ff4d4d", width=0.6)

    # Valores dentro das barras
    for barra in barras:
        altura = barra.get_height()
        plt.text(
            barra.get_x() + barra.get_width() / 2,
            altura / 2,
            f"{altura:g}",
            ha="center",
            va="center",
            fontsize=7,
            color="black"
        )

    # Aparência
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=8)

    plt.xticks(x, testes, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Intensidade / Resultado", fontsize=8)
    plt.title("Testes de Dor", fontsize=9)
    plt.tight_layout()

    # Converte para base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    return image_base64

def visualizar_relatorio(request, paciente_id):
    paciente = Usuário.objects.get(id=paciente_id)

    # Logo
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logoletrapreta.png")
    with open(logo_path, "rb") as img_file:
        logo_base64 = base64.b64encode(img_file.read()).decode("utf-8")

    idade = calcular_idade(paciente.data_de_nascimento)

    # Gera o gráfico
    grafico_forca_base64 = gerar_grafico_forca_muscular(paciente)
    grafico_mobilidade_base64 = gerar_grafico_mobilidade(paciente)
    grafico_estabilidade_base64 = gerar_grafico_estabilidade(paciente)
    grafico_dor_base64 = gerar_grafico_dor(paciente)
    grafico_funcao_base64 = gerar_grafico_funcao(paciente)

    # Cria uma breve análise textual (opcional)
    analise_forca_muscular = "Análise não disponível."
    if grafico_forca_base64:
        analise_forca_muscular = "Distribuição comparativa da força muscular entre os lados direito e esquerdo."

    analise_mobilidade = (
    "Distribuição comparativa da mobilidade entre os lados direito e esquerdo."
    if grafico_mobilidade_base64 else "Análise não disponível."
)
    
    context = {
        "nome": paciente.nome,
        "cpf": paciente.cpf,
        "email": paciente.email,
        "telefone": paciente.telefone,
        "endereço": paciente.endereço,
        "data_de_nascimento": paciente.data_de_nascimento,
        "idade": idade,
        "logo_base64": logo_base64,
        "grafico_forca": grafico_forca_base64,
        "grafico_mobilidade": grafico_mobilidade_base64,
        "grafico_estabilidade": grafico_estabilidade_base64,
        "grafico_dor": grafico_dor_base64,
        "grafico_funcao": grafico_funcao_base64,

    }

    return render(request, "relatorio.html", context)

from rest_framework.decorators import api_view, permission_classes

@api_view(['GET'])
@permission_classes([AllowAny])
def relatorio_publico(request, token):
    """
    Retorna o relatório público de um paciente a partir de um token permanente.
    """
    try:
        relatorio = RelatorioPublico.objects.get(token=token, ativo=True)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({'erro': 'Relatório não encontrado ou inativo'}, status=404)

    dados = {
        'paciente': paciente.nome,
        'forca': list(ForcaMuscular.objects.filter(paciente=paciente).values()),
        'mobilidade': list(Mobilidade.objects.filter(paciente=paciente).values()),
        'funcao': list(TesteFuncao.objects.filter(paciente=paciente).values()),
        'dor': list(TesteDor.objects.filter(paciente=paciente).values()),
    }

    return Response(dados)
from django.db.models import Max
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ForcaMuscular, RelatorioPublico
from django.urls import reverse
import secrets


@api_view(['POST'])
@permission_classes([AllowAny])
def gerar_relatorio(request, paciente_id):
    paciente = get_object_or_404(Usuário, id=paciente_id)

    # Se já existir um relatório para esse paciente, pode criar outro ou usar o existente
    relatorio, criado = RelatorioPublico.objects.get_or_create(
        paciente=paciente,
        defaults={'token': secrets.token_urlsafe(32)}
    )

    # Monta a URL completa do relatório
    url_relatorio = request.build_absolute_uri(
        reverse('relatorio-publico', args=[relatorio.token])
    )

    return Response({"url": url_relatorio}, status=201)

@api_view(['GET'])
@permission_classes([AllowAny])
def forca_publica(request, token):
    try:
        relatorio = RelatorioPublico.objects.get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    # 🔹 Se há data específica, retorna apenas dessa data
    if data_avaliacao:
        dados = (
            ForcaMuscular.objects
            .filter(paciente=paciente, data_avaliacao=data_avaliacao)
            .values('id', 'movimento_forca__nome', 'lado_esquerdo', 'lado_direito', 'data_avaliacao')
            .order_by('id')  # 👈 ordenação padronizada
        )
        return Response(dados)

    # 🔹 Caso contrário, traz o último registro de cada movimento
    subquery = (
        ForcaMuscular.objects
        .filter(paciente=paciente)
        .values('movimento_forca')
        .annotate(ultima_data=Max('data_avaliacao'))
    )

    dados = (
        ForcaMuscular.objects
        .filter(
            paciente=paciente,
            data_avaliacao__in=[i['ultima_data'] for i in subquery]
        )
        .values('id', 'movimento_forca__nome', 'lado_esquerdo', 'lado_direito', 'data_avaliacao')
        .order_by('id')  # 👈 igual aqui também
    )

    return Response(dados)

@api_view(['GET'])
@permission_classes([AllowAny])
def mobilidade_publica(request, token):
    try:
        relatorio = RelatorioPublico.objects.get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = Mobilidade.objects.filter(paciente=paciente, data_avaliacao=data_avaliacao)
    else:
        subquery = (
            Mobilidade.objects
            .filter(paciente=paciente)
            .values('nome')
            .annotate(ultima_data=Max('data_avaliacao'))
        )
        queryset = Mobilidade.objects.filter(
            paciente=paciente,
            data_avaliacao__in=[i['ultima_data'] for i in subquery]
        ).order_by('id')  # 🔹 garante ordem consistente

        

    serializer = MobilidadeSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def estabilidade_publica(request, token):
    """
    Endpoint público para retornar dados de estabilidade de um paciente,
    usando o token de relatório público.
    """
    try:
        relatorio = RelatorioPublico.objects.get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = Estabilidade.objects.filter(
            paciente=paciente,
            data_avaliacao=data_avaliacao
        ).order_by('id')  # 🔹 garante ordem consistente
    else:
        # Pega o último registro de cada movimento
        subquery = (
            Estabilidade.objects
            .filter(paciente=paciente)
            .values('movimento_estabilidade')
            .annotate(ultima_data=Max('data_avaliacao'))
        )
        queryset = Estabilidade.objects.filter(
            paciente=paciente,
            data_avaliacao__in=[i['ultima_data'] for i in subquery]
        ).order_by('id')  # 🔹 garante ordem consistente

    serializer = EstabilidadeSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def funcao_publica(request, token):
    """
    Endpoint público para retornar dados de função de um paciente,
    usando o token de relatório público.
    """
    try:
        relatorio = RelatorioPublico.objects.get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = TesteFuncao.objects.filter(
            paciente=paciente,
            data_avaliacao=data_avaliacao
        ).order_by('id')  # garante ordem consistente
    else:
        # Pega o último registro de cada teste
        subquery = (
            TesteFuncao.objects
            .filter(paciente=paciente)
            .values('teste_id')
            .annotate(ultima_data=Max('data_avaliacao'))
        )
        queryset = TesteFuncao.objects.filter(
            paciente=paciente,
            data_avaliacao__in=[i['ultima_data'] for i in subquery]
        ).order_by('id')  # garante ordem consistente

    serializer = TesteFuncaoSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def dor_publica(request, token):
    """
    Endpoint público para retornar dados de dor de um paciente via token de relatório público.
    """
    try:
        relatorio = RelatorioPublico.objects.get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = TesteDor.objects.filter(
            paciente=paciente,
            data_avaliacao=data_avaliacao
        ).order_by('id')  # 🔹 garante ordem consistente
    else:
        # Pega o último registro de cada teste
        subquery = (
            TesteDor.objects
            .filter(paciente=paciente)
            .values('teste')
            .annotate(ultima_data=Max('data_avaliacao'))
        )
        queryset = TesteDor.objects.filter(
            paciente=paciente,
            data_avaliacao__in=[i['ultima_data'] for i in subquery]
        ).order_by('id')  # 🔹 garante ordem consistente

    serializer = TesteDorSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def datas_disponiveis_publicas(request, token):
    try:
        relatorio = RelatorioPublico.objects.get(token=token)
        paciente = relatorio.paciente

        # 🔹 Obter datas distintas de cada modelo
        datas_forca = ForcaMuscular.objects.filter(paciente=paciente).values_list('data_avaliacao', flat=True)
        datas_mobilidade = Mobilidade.objects.filter(paciente=paciente).values_list('data_avaliacao', flat=True)
        datas_estabilidade = Estabilidade.objects.filter(paciente=paciente).values_list('data_avaliacao', flat=True)
        datas_funcao = TesteFuncao.objects.filter(paciente=paciente).values_list('data_avaliacao', flat=True)
        datas_dor = TesteDor.objects.filter(paciente=paciente).values_list('data_avaliacao', flat=True)

        # 🔹 Unir todas as datas em um set para garantir unicidade
        todas_datas = set(datas_forca) | set(datas_mobilidade) | set(datas_estabilidade) | set(datas_funcao) | set(datas_dor)

        # 🔹 Ordenar do mais recente para o mais antigo
        datas_ordenadas = sorted(todas_datas, reverse=True)

        return Response(datas_ordenadas)

    except RelatorioPublico.DoesNotExist:
        return Response({'detail': 'Token inválido.'}, status=404)