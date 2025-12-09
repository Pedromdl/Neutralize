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
from django.db.models import Max, OuterRef, Subquery, Q

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
    UsuarioBaseSerializer, UsuarioDetailSerializer, EstabilidadeSerializer, ForcaMuscularSerializer, MobilidadeSerializer,
    CategoriaTesteSerializer, TodosTestesSerializer, TesteFuncaoSerializer, TesteDorSerializer, 
    PreAvaliacaoSerializer, AnamneseSerializer, EventoSerializer, SessaoSerializer
)
from .mixins import OrganizacaoFilterMixin


class UsuárioViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    queryset = Usuário.objects.all()
    # Remova o serializer_class fixo, vamos definir dinamicamente
    permission_classes = [IsAuthenticated]
    organizacao_field = "organizacao"

    def get_serializer_class(self):
        """
        Escolhe dinamicamente o serializer baseado na ação:
        - list: UsuarioBaseSerializer (rápido, sem dados sensíveis)
        - retrieve: UsuarioBaseSerializer (padrão) ou Detail se solicitado
        - create/update/partial_update: UsuarioDetailSerializer (todos os campos)
        - Outras ações: UsuarioBaseSerializer
        """
        # Ação 'list' - SEMPRE usar base para performance
        if self.action == 'list':
            return UsuarioBaseSerializer
        
        # Ações que precisam de todos os campos
        if self.action in ['create', 'update', 'partial_update']:
            return UsuarioDetailSerializer
        
        # Ação 'retrieve' - verifica se quer detalhes completos
        if self.action == 'retrieve':
            # Verifica parâmetro de query ou header
            request = self.request
            if request:
                # Opção 1: Via query parameter ?detalhes=completo
                if request.query_params.get('detalhes') == 'completo':
                    if request.user.has_perm('usuarios.view_sensitive_data'):
                        return UsuarioDetailSerializer
                
                # Opção 2: Via header HTTP_X_DETAILS=full
                if request.META.get('HTTP_X_DETAILS') == 'full':
                    if request.user.has_perm('usuarios.view_sensitive_data'):
                        return UsuarioDetailSerializer
        
        # Padrão para retrieve e outras ações
        return UsuarioBaseSerializer

    def get_queryset(self):
        """
        Otimiza o queryset baseado na ação para melhor performance
        """
        queryset = super().get_queryset()
        
        # Para listas, seleciona apenas os campos necessários
        if self.action == 'list':
            # ONLY - seleciona apenas estes campos do banco
            queryset = queryset.only(
                'id', 
                'nome', 
                'email', 
                'organizacao_id',
            ).select_related('organizacao')  # Junta organização em uma query
        
        # Para retrieve com base serializer, também otimiza
        elif self.action == 'retrieve' and self.get_serializer_class() == UsuarioBaseSerializer:
            queryset = queryset.only(
                'id', 'nome', 'email', 'organizacao_id'
            ).select_related('organizacao')
        
        return queryset

    def list(self, request, *args, **kwargs):
        """
        Lista otimizada - apenas dados básicos
        """
        response = super().list(request, *args, **kwargs)
        
        # Log de acesso à lista
        log_acesso(
            usuario=request.user,
            paciente_id=0,
            acao="listou",
            campo="usuário",
            request=request,
            detalhes=f"Listou usuários (total: {len(response.data)})"
        )
        
        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Determina o nível de detalhe para o log
        serializer_class = self.get_serializer_class()
        nivel_detalhe = "completos" if serializer_class == UsuarioDetailSerializer else "básicos"
        
        # Log de acesso
        log_acesso(
            usuario=request.user,
            paciente_id=getattr(instance, "id", None),
            acao="visualizou",
            campo="usuário",
            request=request,
            detalhes=f"Visualizou dados {nivel_detalhe} de usuário"
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Criação - usa serializer completo
        """
        response = super().create(request, *args, **kwargs)
        
        # Log de criação
        if response.status_code == 201:  # Created
            usuario_id = response.data.get('id')
            log_acesso(
                usuario=request.user,
                paciente_id=usuario_id,
                acao="criou",
                campo="usuário",
                request=request,
                detalhes="Criou novo usuário"
            )
        
        return response

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Chamar log ANTES da atualização (para capturar dados antigos se necessário)
        log_acesso(
            usuario=request.user,
            paciente_id=getattr(instance, "id", None),
            acao="editou",
            campo="usuário",
            request=request,
            detalhes="Atualizou dados de usuário"
        )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Chamar log
        log_acesso(
            usuario=request.user,
            paciente_id=getattr(instance, "id", None),
            acao="deletou",
            campo="usuário",
            request=request,
            detalhes="Deletou usuário"
        )

        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def dados_completos(self, request, pk=None):
        """
        Endpoint específico para dados completos
        URL: /api/usuarios/{id}/dados_completos/
        """
        usuario = self.get_object()
        
        # Verifica permissão específica para dados sensíveis
        if not request.user.has_perm('usuarios.view_sensitive_data'):
            return Response(
                {"detail": "Você não tem permissão para visualizar dados sensíveis"},
                status=403
            )
        
        # Log específico para acesso a dados sensíveis
        log_acesso(
            usuario=request.user,
            paciente_id=usuario.id,
            acao="visualizou_sensivel",
            campo="usuário",
            request=request,
            detalhes="Visualizou dados sensíveis completos do usuário via endpoint específico"
        )
        
        serializer = UsuarioDetailSerializer(usuario, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def busca_rapida(self, request):
        """
        Endpoint para busca rápida - apenas id, nome, email
        Útil para autocomplete, select boxes, etc.
        """
        termo = request.query_params.get('q', '')
        
        if termo:
            queryset = self.get_queryset().filter(
                Q(nome__icontains=termo) | Q(email__icontains=termo)
            )[:20]  # Limita a 20 resultados
        else:
            queryset = self.get_queryset().none()
        
        serializer = UsuarioBaseSerializer(queryset, many=True)
        
        return Response(serializer.data)

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


# views.py
from rest_framework import viewsets, permissions, serializers
from .models import CategoriaTeste
from .serializers import CategoriaTesteSerializer

class CategoriaTesteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gerenciar categorias de teste.
    """
    queryset = CategoriaTeste.objects.all()
    serializer_class = CategoriaTesteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filtro opcional por nome
        """
        queryset = CategoriaTeste.objects.all()
        nome = self.request.query_params.get('nome', None)
        
        if nome:
            queryset = queryset.filter(nome__icontains=nome)
            
        return queryset

    def perform_create(self, serializer):
        """
        Garante que não haja duplicação (já que nome é unique)
        """
        nome = serializer.validated_data.get('nome')
        if CategoriaTeste.objects.filter(nome__iexact=nome).exists():
            raise serializers.ValidationError(
                {'nome': 'Uma categoria com este nome já existe.'}
            )
        serializer.save()

    def perform_update(self, serializer):
        """
        Garante que a atualização não crie duplicação
        """
        nome = serializer.validated_data.get('nome')
        instance = self.get_object()
        
        if CategoriaTeste.objects.filter(nome__iexact=nome).exclude(id=instance.id).exists():
            raise serializers.ValidationError(
                {'nome': 'Uma categoria com este nome já existe.'}
            )
        serializer.save()


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

class PreAvaliacaoViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PreAvaliacao.objects.all()
    serializer_class = PreAvaliacaoSerializer
    organizacao_field = "organizacao"

class AnamneseViewSet(viewsets.ModelViewSet):
    queryset = Anamnese.objects.all()
    serializer_class = AnamneseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['paciente']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        log_acesso(
            usuario=request.user,
            paciente_id=getattr(instance, "paciente_id", None),
            acao="visualizou",
            campo="anamnese",
            request=request,
            detalhes="Visualizou anamnese"
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        log_acesso(
            usuario=request.user,
            paciente_id=getattr(instance, "paciente_id", None),
            acao="editou",
            campo="anamnese",
            request=request,
            detalhes="Atualizou anamnese"
        )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        log_acesso(
            usuario=request.user,
            paciente_id=getattr(instance, "paciente_id", None),
            acao="deletou",
            campo="anamnese",
            request=request,
            detalhes="Deletou anamnese"
        )

        return super().destroy(request, *args, **kwargs)


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
    
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
import base64, os
from django.conf import settings
from .models import Usuário


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
        logo_base64 = ""

    idade = calcular_idade(paciente.data_de_nascimento)

    # ✅ Gera os gráficos com base na data selecionada
    grafico_forca_base64 = gerar_grafico_forca_muscular(paciente, data_selecionada)
    grafico_mobilidade_base64 = gerar_grafico_mobilidade(paciente, data_selecionada)
    grafico_estabilidade_base64 = gerar_grafico_estabilidade(paciente, data_selecionada)
    grafico_dor_base64 = gerar_grafico_dor(paciente, data_selecionada)
    grafico_funcao_base64 = gerar_grafico_funcao(paciente, data_selecionada)

    # Renderiza o HTML
    html_string = render_to_string("relatorio.html", {
        "logo_base64": logo_base64,
        "nome": paciente.nome,
        "cpf": paciente.cpf,
        "email": paciente.email,
        "telefone": paciente.telefone,
        "data_de_nascimento": paciente.data_de_nascimento,
        "idade": idade,
        "grafico_forca": grafico_forca_base64,
        "grafico_mobilidade": grafico_mobilidade_base64,
        "grafico_estabilidade": grafico_estabilidade_base64,
        "grafico_dor": grafico_dor_base64,
        "grafico_funcao": grafico_funcao_base64,
    })

    # Gera o PDF diretamente do HTML
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(
        stylesheets=[CSS(string="""
            @page { size: A4; margin: 10mm; }
            body { font-family: 'Arial', sans-serif; }
            img { max-width: 100%; height: auto; }
        """)]
    )

    # Retorna o PDF como download
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="relatorio_{paciente.nome}.pdf"'
    return response



def calcular_idade(data_nascimento):
    if not data_nascimento:
        return None
    hoje = date.today()
    return hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )

from matplotlib.colors import to_rgb
from io import BytesIO
import matplotlib.pyplot as plt
import base64
from django.db.models import Max

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

    # Valores dentro das barras com contraste automático
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            r, g, b = to_rgb(barra.get_facecolor())  # converte cor da barra para RGB 0-1
            luminancia = 0.2126*r + 0.7152*g + 0.0722*b
            cor_texto = "black" if luminancia > 0.5 else "white"

            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{altura:g}",
                ha="center",
                va="center",
                fontsize=7,
                color=cor_texto,
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

    qs = Mobilidade.objects.filter(paciente=paciente)
    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)

    ultimas_avaliacoes = qs.values("nome__nome").annotate(data_mais_recente=Max("data_avaliacao"))
    dados = [qs.filter(nome__nome=item["nome__nome"], data_avaliacao=item["data_mais_recente"]).first()
             for item in ultimas_avaliacoes if qs.filter(nome__nome=item["nome__nome"], data_avaliacao=item["data_mais_recente"]).exists()]

    if not dados:
        return None

    testes = [d.nome.nome if d.nome else "Teste" for d in dados]
    lado_esquerdo = [float(d.lado_esquerdo) for d in dados]
    lado_direito = [float(d.lado_direito) for d in dados]

    plt.figure(figsize=(4.2, 3))
    x = range(len(testes))
    largura = 0.45

    barras_esq = plt.bar([i - largura / 2 for i in x], lado_esquerdo, width=largura, label="Lado Esquerdo", color="#b7de42")
    barras_dir = plt.bar([i + largura / 2 for i in x], lado_direito, width=largura, label="Lado Direito", color="#282829")

    # Valores dentro das barras com contraste automático
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            r, g, b = to_rgb(barra.get_facecolor())
            luminancia = 0.2126*r + 0.7152*g + 0.0722*b
            cor_texto = "black" if luminancia > 0.5 else "white"

            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{int(altura)}",
                ha="center",
                va="center",
                fontsize=7,
                color=cor_texto
            )

    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=6)

    plt.xticks(x, testes, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Amplitude (°)", fontsize=8)
    plt.legend(fontsize=7)
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def gerar_grafico_estabilidade(paciente, data_selecionada=None):
    print(f"[DEBUG] gerando gráfico de estabilidade para paciente: {paciente.nome}")
    print(f"[DEBUG] data_selecionada: {data_selecionada}")

    qs = Estabilidade.objects.filter(paciente=paciente)
    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)

    ultimas_avaliacoes = qs.values("movimento_estabilidade__nome").annotate(data_mais_recente=Max("data_avaliacao"))
    dados = [qs.filter(movimento_estabilidade__nome=item["movimento_estabilidade__nome"], data_avaliacao=item["data_mais_recente"]).first()
             for item in ultimas_avaliacoes if qs.filter(movimento_estabilidade__nome=item["movimento_estabilidade__nome"], data_avaliacao=item["data_mais_recente"]).exists()]

    if not dados:
        return None

    movimentos = [d.movimento_estabilidade.nome if d.movimento_estabilidade else "Movimento" for d in dados]
    lado_esquerdo = [float(d.lado_esquerdo) if d.lado_esquerdo else 0 for d in dados]
    lado_direito = [float(d.lado_direito) if d.lado_direito else 0 for d in dados]

    plt.figure(figsize=(4.2, 3))
    x = range(len(movimentos))
    largura = 0.45

    barras_esq = plt.bar([i - largura / 2 for i in x], lado_esquerdo, width=largura, label="Lado Esquerdo", color="#b7de42")
    barras_dir = plt.bar([i + largura / 2 for i in x], lado_direito, width=largura, label="Lado Direito", color="#282829")

    # Valores dentro das barras com contraste automático
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            r, g, b = to_rgb(barra.get_facecolor())
            luminancia = 0.2126*r + 0.7152*g + 0.0722*b
            cor_texto = "black" if luminancia > 0.5 else "white"

            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{altura:g}",
                ha="center",
                va="center",
                fontsize=7,
                color=cor_texto
            )

    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=8)

    plt.xticks(x, movimentos, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Pontuação / Tempo", fontsize=8)
    plt.legend(fontsize=7)
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
def gerar_grafico_funcao(paciente, data_selecionada=None):
    print(f"[DEBUG] gerando gráfico de função para paciente: {paciente.nome}")
    qs = TesteFuncao.objects.filter(paciente=paciente)
    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)

    ultimas_avaliacoes = qs.values("teste__nome").annotate(data_mais_recente=Max("data_avaliacao"))
    dados = [qs.filter(teste__nome=item["teste__nome"], data_avaliacao=item["data_mais_recente"]).first()
             for item in ultimas_avaliacoes if qs.filter(teste__nome=item["teste__nome"], data_avaliacao=item["data_mais_recente"]).exists()]

    if not dados:
        return None

    testes = [d.teste.nome if d.teste else "Teste" for d in dados]
    lado_esquerdo = [float(d.lado_esquerdo) if d.lado_esquerdo else 0 for d in dados]
    lado_direito = [float(d.lado_direito) if d.lado_direito else 0 for d in dados]

    plt.figure(figsize=(4.2, 3))
    x = range(len(testes))
    largura = 0.45

    barras_esq = plt.bar([i - largura / 2 for i in x], lado_esquerdo, width=largura, label="Lado Esquerdo", color="#b7de42")
    barras_dir = plt.bar([i + largura / 2 for i in x], lado_direito, width=largura, label="Lado Direito", color="#282829")

    # Valores dentro das barras com contraste automático
    for barras in [barras_esq, barras_dir]:
        for barra in barras:
            altura = barra.get_height()
            r, g, b = to_rgb(barra.get_facecolor())
            luminancia = 0.2126*r + 0.7152*g + 0.0722*b
            cor_texto = "black" if luminancia > 0.5 else "white"
            plt.text(
                barra.get_x() + barra.get_width() / 2,
                altura / 2,
                f"{altura:g}",
                ha="center",
                va="center",
                fontsize=7,
                color=cor_texto
            )

    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=8)
    plt.xticks(x, testes, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Pontuação / Tempo", fontsize=8)
    plt.legend(fontsize=7)
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def gerar_grafico_dor(paciente, data_selecionada=None):
    print(f"[DEBUG] gerando gráfico de dor para paciente: {paciente.nome}")
    qs = TesteDor.objects.filter(paciente=paciente)
    if data_selecionada:
        qs = qs.filter(data_avaliacao=data_selecionada)

    ultimas_avaliacoes = qs.values("teste__nome").annotate(data_mais_recente=Max("data_avaliacao"))
    dados = [qs.filter(teste__nome=item["teste__nome"], data_avaliacao=item["data_mais_recente"]).first()
             for item in ultimas_avaliacoes if qs.filter(teste__nome=item["teste__nome"], data_avaliacao=item["data_mais_recente"]).exists()]

    if not dados:
        # Placeholder quando não há dados
        plt.figure(figsize=(4.2, 3))
        plt.text(0.5, 0.5, 'Sem dados', ha='center', va='center', fontsize=12, color='gray')
        plt.axis('off')
        buffer = BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
        plt.close()
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    testes = [d.teste.nome if d.teste else "Teste" for d in dados]
    resultados = [float(d.resultado) if d.resultado else 0 for d in dados]

    plt.figure(figsize=(4.2, 3))
    x = range(len(testes))
    barras = plt.bar(x, resultados, color="#ff4d4d", width=0.6)

    # Valores dentro das barras com contraste automático
    for barra in barras:
        altura = barra.get_height()
        r, g, b = to_rgb(barra.get_facecolor())
        luminancia = 0.2126*r + 0.7152*g + 0.0722*b
        cor_texto = "black" if luminancia > 0.5 else "white"
        plt.text(
            barra.get_x() + barra.get_width() / 2,
            altura / 2,
            f"{altura:g}",
            ha="center",
            va="center",
            fontsize=7,
            color=cor_texto
        )

    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=8)
    plt.xticks(x, testes, rotation=30, ha="right", fontsize=6)
    plt.ylabel("Intensidade / Resultado", fontsize=8)
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close()
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")

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
        'paciente': list(Usuário.objects.filter(id=paciente.id).values()),
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
from django.db.models import Max, Subquery, OuterRef
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import (
    RelatorioPublico, ForcaMuscular, Mobilidade, Estabilidade,
    TesteFuncao, TesteDor
)
from .serializers import (
    MobilidadeSerializer, EstabilidadeSerializer,
    TesteFuncaoSerializer, TesteDorSerializer
)

# ============================
# 1️⃣ Dados do usuário
# ============================
@api_view(['GET'])
@permission_classes([AllowAny])
def usuario_publico(request, token):
    try:
        # SELECT + JOIN para evitar 2 consultas
        relatorio = RelatorioPublico.objects.select_related('paciente').get(token=token, ativo=True)
        usuario = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({'erro': 'Relatório não encontrado ou inativo'}, status=404)

    dados = {
        'id': usuario.id,
        'nome': usuario.nome,
        'cpf': usuario.cpf,
        'email': usuario.email,
        'telefone': usuario.telefone,
        'endereço': usuario.endereço,
        'data_de_nascimento': usuario.data_de_nascimento,
        'user_id': usuario.user_id,
    }
    return Response(dados)


# ============================
# 2️⃣ Força Muscular
# ============================
@api_view(['GET'])
@permission_classes([AllowAny])
def forca_publica(request, token):
    try:
        relatorio = RelatorioPublico.objects.select_related('paciente').get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        dados = (
            ForcaMuscular.objects
            .filter(paciente=paciente, data_avaliacao=data_avaliacao)
            .values('id', 'movimento_forca__nome', 'lado_esquerdo', 'lado_direito', 'data_avaliacao')
            .order_by('id')
        )
    else:
        # Subquery otimizada
        ultima_data = ForcaMuscular.objects.filter(
            paciente=paciente,
            movimento_forca=OuterRef('movimento_forca')
        ).values('data_avaliacao').order_by('-data_avaliacao')[:1]

        dados = (
            ForcaMuscular.objects
            .filter(paciente=paciente, data_avaliacao=Subquery(ultima_data))
            .values('id', 'movimento_forca__nome', 'lado_esquerdo', 'lado_direito', 'data_avaliacao')
            .order_by('id')
        )

    return Response(dados)


# ============================
# 3️⃣ Mobilidade
# ============================
@api_view(['GET'])
@permission_classes([AllowAny])
def mobilidade_publica(request, token):
    try:
        relatorio = RelatorioPublico.objects.select_related('paciente').get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = Mobilidade.objects.filter(paciente=paciente, data_avaliacao=data_avaliacao)
    else:
        ultima_data = Mobilidade.objects.filter(
            paciente=paciente,
            nome=OuterRef('nome')
        ).values('data_avaliacao').order_by('-data_avaliacao')[:1]

        queryset = Mobilidade.objects.filter(
            paciente=paciente,
            data_avaliacao=Subquery(ultima_data)
        ).order_by('id')

    serializer = MobilidadeSerializer(queryset, many=True)
    return Response(serializer.data)


# ============================
# 4️⃣ Estabilidade
# ============================
@api_view(['GET'])
@permission_classes([AllowAny])
def estabilidade_publica(request, token):
    try:
        relatorio = RelatorioPublico.objects.select_related('paciente').get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = Estabilidade.objects.filter(paciente=paciente, data_avaliacao=data_avaliacao).order_by('id')
    else:
        ultima_data = Estabilidade.objects.filter(
            paciente=paciente,
            movimento_estabilidade=OuterRef('movimento_estabilidade')
        ).values('data_avaliacao').order_by('-data_avaliacao')[:1]

        queryset = Estabilidade.objects.filter(
            paciente=paciente,
            data_avaliacao=Subquery(ultima_data)
        ).order_by('id')

    serializer = EstabilidadeSerializer(queryset, many=True)
    return Response(serializer.data)


# ============================
# 5️⃣ Função
# ============================
@api_view(['GET'])
@permission_classes([AllowAny])
def funcao_publica(request, token):
    try:
        relatorio = RelatorioPublico.objects.select_related('paciente').get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = TesteFuncao.objects.filter(paciente=paciente, data_avaliacao=data_avaliacao).order_by('id')
    else:
        ultima_data = TesteFuncao.objects.filter(
            paciente=paciente,
            teste_id=OuterRef('teste_id')
        ).values('data_avaliacao').order_by('-data_avaliacao')[:1]

        queryset = TesteFuncao.objects.filter(
            paciente=paciente,
            data_avaliacao=Subquery(ultima_data)
        ).order_by('id')

    serializer = TesteFuncaoSerializer(queryset, many=True)
    return Response(serializer.data)


# ============================
# 6️⃣ Dor
# ============================
@api_view(['GET'])
@permission_classes([AllowAny])
def dor_publica(request, token):
    try:
        relatorio = RelatorioPublico.objects.select_related('paciente').get(token=token)
        paciente = relatorio.paciente
    except RelatorioPublico.DoesNotExist:
        return Response({"detail": "Token inválido"}, status=404)

    data_avaliacao = request.GET.get('data_avaliacao')

    if data_avaliacao:
        queryset = TesteDor.objects.filter(paciente=paciente, data_avaliacao=data_avaliacao).order_by('id')
    else:
        ultima_data = TesteDor.objects.filter(
            paciente=paciente,
            teste=OuterRef('teste')
        ).values('data_avaliacao').order_by('-data_avaliacao')[:1]

        queryset = TesteDor.objects.filter(
            paciente=paciente,
            data_avaliacao=Subquery(ultima_data)
        ).order_by('id')

    serializer = TesteDorSerializer(queryset, many=True)
    return Response(serializer.data)


# ============================
# 7️⃣ Datas disponíveis
# ============================
@api_view(['GET'])
@permission_classes([AllowAny])
def datas_disponiveis_publicas(request, token):
    try:
        relatorio = RelatorioPublico.objects.select_related('paciente').get(token=token)
        paciente = relatorio.paciente

        # União otimizada via UNION SQL
        todas_datas = (
            ForcaMuscular.objects.filter(paciente=paciente).values_list('data_avaliacao')
            .union(
                Mobilidade.objects.filter(paciente=paciente).values_list('data_avaliacao'),
                Estabilidade.objects.filter(paciente=paciente).values_list('data_avaliacao'),
                TesteFuncao.objects.filter(paciente=paciente).values_list('data_avaliacao'),
                TesteDor.objects.filter(paciente=paciente).values_list('data_avaliacao'),
            )
        )

        datas_ordenadas = sorted({d[0] for d in todas_datas}, reverse=True)
        return Response(datas_ordenadas)

    except RelatorioPublico.DoesNotExist:
        return Response({'detail': 'Token inválido.'}, status=404)


from .utils import log_acesso

def get_paciente_detail(request, paciente_id):
    paciente = Usuário.objects.get(id=paciente_id)

    # Registrar log de acesso
    log_acesso(
        usuario=request.user,
        paciente_id=paciente.id,
        acao="visualizou",
        campo="prontuário",
        request=request
    )

    return Response({
        "nome": paciente.nome,
    })