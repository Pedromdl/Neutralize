from django.conf import settings  # importe settings do Django
from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone
from datetime import timedelta


from rest_framework import generics, permissions, filters, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied


from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from api.mixins import OrganizacaoFilterMixin

from .serializers import OrganizacaoListSerializer, OrganizacaoSerializer , CustomUserSerializer, DocumentoLegalSerializer, AceiteDocumentoSerializer
from .models import Organizacao, DocumentoLegal, CustomUser
from api.models import Usuário  # ← MOVER PARA DENTRO DO MÉTODO

from api.models import Usuário
from pagamentos.models import PlanoPagamento, Assinatura, ProvedorPagamento
from pagamentos.services.asaas_service import AsaasService

User = get_user_model()

class OrganizacaoDetailView(generics.RetrieveUpdateAPIView):
    """
    View para visualizar e atualizar os dados da organização do usuário atual.
    Retorna 404 se o usuário não tiver organização associada.
    """
    serializer_class = OrganizacaoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Verifica se o usuário tem organização associada
        if not self.request.user.organizacao:
            raise Http404("Este usuário não possui uma organização associada.")
        return self.request.user.organizacao
    
    def update(self, request, *args, **kwargs):
        # PATCH ou PUT parcial
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    

class CustomUserViewSet(OrganizacaoFilterMixin, viewsets.ModelViewSet):
    """
    CRUD completo de CustomUser:
    - create: cria usuário na organização do admin logado
    - list: lista apenas usuários da organização
    - retrieve: obtém um usuário específico
    - update/partial_update: editar usuário
    - destroy: deletar usuário
    """

    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CustomUser.objects.all()
    organizacao_field = "organizacao"   # <-- ESSENCIAL

    # ----------------------------------------------------------------------

    def perform_create(self, serializer):
        """
        Garante que o usuário criado pertence à mesma organização do usuário logado.
        Ignora organização enviada pelo frontend.
        """
        user = self.request.user

        serializer.save(organizacao=user.organizacao)

    # ----------------------------------------------------------------------

    def perform_destroy(self, instance):
        """
        Impede que alguém delete usuários de outra organização (segurança extra).
        """
        if instance.organizacao != self.request.user.organizacao:
            raise PermissionDenied("Você não pode deletar usuários de outra organização.")
        instance.delete()

    # ----------------------------------------------------------------------

    def perform_update(self, serializer):
        """
        Garante que a edição não troque o usuário de organização.
        """
        user = self.request.user
        if serializer.instance.organizacao != user.organizacao:
            raise PermissionDenied("Você não pode editar usuários de outra organização.")

        serializer.save(organizacao=user.organizacao)  # força permanência

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        print("Usuário autenticado na requisição:", self.request.user)
        return self.request.user
    
class UserListView(OrganizacaoFilterMixin, generics.ListAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CustomUser.objects.all()
    organizacao_field = "organizacao"   # <-- ESSENCIAL
    filter_backends = [filters.OrderingFilter]  # <— habilita ordenação
    ordering_fields = ['id', 'first_name', 'email', 'role']   # <— campos liberados
    ordering = ['id']  # ordenação padrão


class RegisterPacienteView(APIView):
    """
    Registro de paciente NO APLICATIVO.
    Somente pacientes que JÁ TEM email cadastrado na clínica podem criar conta.
    """
    
    def post(self, request):
        email = request.data.get("email", "").strip()
        password = request.data.get("password", "").strip()
        
        # Validações básicas
        if not email or not password:
            return Response(
                {"error": "Email e senha são obrigatórios."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica se já existe CustomUser com este email
        if CustomUser.objects.filter(email__iexact=email).exists():
            return Response(
                {"error": "Este email já possui uma conta cadastrada."},
                status=status.HTTP_400_BAD_REQUEST
            )
                
        try:
            # Busca o Usuário pelo email EXATO
            usuario_existente = Usuário.objects.get(email__iexact=email)
            
            # Verifica se já tem CustomUser vinculado
            if usuario_existente.user:
                return Response(
                    {"error": "Este email já possui uma conta ativa."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Separa nome completo em first_name e last_name
            nome_parts = usuario_existente.nome.split(' ', 1)
            first_name = nome_parts[0]
            last_name = nome_parts[1] if len(nome_parts) > 1 else ""
            
            # Cria o CustomUser
            custom_user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='paciente',
                organizacao=usuario_existente.organizacao,
                cpf=usuario_existente.cpf,
                phone=usuario_existente.telefone,
                birth_date=usuario_existente.data_de_nascimento,
                # Endereço pode ser copiado se quiser
                address=f"{usuario_existente.rua}, {usuario_existente.numero} - {usuario_existente.bairro}" 
                        if usuario_existente.rua else ""
            )
            
            # Vincula o CustomUser ao Usuário
            usuario_existente.user = custom_user
            usuario_existente.save()
            
            # Gera tokens JWT para login automático
            refresh = RefreshToken.for_user(custom_user)
            
            return Response({
                "success": True,
                "message": "Conta criada com sucesso!",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                },
                "user": {
                    "id": custom_user.id,
                    "email": custom_user.email,
                    "first_name": custom_user.first_name,
                    "last_name": custom_user.last_name,
                    "role": custom_user.role,
                    "organizacao_id": custom_user.organizacao.id if custom_user.organizacao else None
                }
            }, status=status.HTTP_201_CREATED)
            
        except Usuário.DoesNotExist:
            # Email não encontrado no cadastro da clínica
            return Response({
                "error": "Email não encontrado no cadastro da clínica. "
                        "Entre em contato com sua clínica para verificar seu cadastro."
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            # Log do erro
            print(f"Erro ao criar conta de paciente: {str(e)}")
            return Response({
                "error": "Erro interno ao processar o cadastro. Tente novamente mais tarde."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GoogleAuthView(APIView):
    def post(self, request):
        token = request.data.get("token")
        print("Token recebido do frontend:", token[:50] + "..." if token else "None")

        client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
        print("Client ID configurado:", client_id)

        if not token:
            return Response({"error": "Token não enviado"}, status=400)

        if not client_id:
            return Response({"error": "Configuração GOOGLE_CLIENT_ID não encontrada"}, status=500)

        try:
            # ✅ CORREÇÃO: Adicione clock_skew_in_seconds
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                client_id,
                clock_skew_in_seconds=10  # Tolerância de 10 segundos
            )

            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")
            photo = idinfo.get("picture", "")

            print(f"Email do token: {email}")

            if not email:
                return Response({"error": "Email não encontrado no token"}, status=400)

            try:
                user = CustomUser.objects.get(email=email)
                # Atualiza dados do Google
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.photo_google = photo or user.photo_google
                user.save()
                print(f"Usuário existente encontrado: {user.email}")
                
            except CustomUser.DoesNotExist:
                # Procura no modelo Usuário
                try:
                    paciente = Usuário.objects.get(email=email)
                    user = CustomUser.objects.create_user(
                        email=email,
                        first_name=first_name or paciente.nome.split()[0],
                        last_name=last_name or " ".join(paciente.nome.split()[1:]),
                        role="paciente",
                        organizacao=paciente.organizacao,
                        photo_google=photo
                    )
                    # Associa o CustomUser ao Usuário
                    paciente.user = user
                    paciente.save()
                    print(f"Novo usuário criado a partir de Usuário: {user.email}")
                    
                except Usuário.DoesNotExist:
                    print(f"Email não encontrado em nenhum modelo: {email}")
                    return Response({"error": "Email não registrado no sistema."}, status=400)

            # Gera tokens JWT
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role
                }
            })

        except ValueError as e:
            print(f"Erro na validação do token: {str(e)}")
            return Response({"error": f"Token inválido: {str(e)}"}, status=400)
        except Exception as e:
            print(f"Erro inesperado: {str(e)}")
            return Response({"error": "Erro interno no servidor"}, status=500)

        
from django.contrib.auth import authenticate

class LoginView(APIView):
    """
    Endpoint para login tradicional com email e senha
    """

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not all([email, password]):
            return Response({"error": "Email e senha são obrigatórios."}, status=400)

        user = authenticate(request, email=email, password=password)
        if user is None:
            return Response({"error": "Usuário ou senha inválidos."}, status=401)

        if not user.is_active:
            return Response({"error": "Usuário inativo."}, status=403)

        # Gera tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        })

        
class DocumentoLegalListView(generics.ListAPIView):
    serializer_class = DocumentoLegalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tipo = self.request.query_params.get('tipo', None)
        qs = DocumentoLegal.objects.filter(ativo=True)
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs.order_by('-data_publicacao')


class RegistrarAceiteDocumentoView(generics.CreateAPIView):
        """
        Cria um registro de aceite do documento para o usuário logado.
        """
        serializer_class = AceiteDocumentoSerializer
        permission_classes = [permissions.IsAuthenticated]

        def perform_create(self, serializer):
            serializer.save(usuario=self.request.user, data_aceite=timezone.now())

            
class RegisterAdminClinicaView(APIView):
    """
    Cria uma organização e um CustomUser administrador.
    Agora sem uso do AssinaturaService.
    """

    def post(self, request):
        email = request.data.get("email", "").strip()
        nome_organizacao = request.data.get("nome", "").strip()
        password = request.data.get("password", "").strip()
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()

        # Validação dos campos obrigatórios
        if not all([email, nome_organizacao, password, first_name, last_name]):
            return Response({"error": "Todos os campos são obrigatórios."}, status=400)

        # Valida email
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from django.db import IntegrityError

        try:
            validate_email(email)
        except ValidationError:
            return Response({"error": "Email inválido."}, status=400)

        # Valida senha mínima
        if len(password) < 6:
            return Response({"error": "A senha deve ter pelo menos 6 caracteres."}, status=400)

        # Checa duplicidade de email
        if CustomUser.objects.filter(email__iexact=email).exists():
            return Response({"error": "Email já cadastrado."}, status=400)

        # ==========================================================
        # 🔹 Detecta tipo de pessoa (CPF ou CNPJ)
        # ==========================================================
        documento = request.data.get("documento", "").strip()
        documento_limpo = "".join(filter(str.isdigit, documento))  # remove pontos, traços, barras

        if len(documento_limpo) == 11:
            tipo_pessoa = "pf"
            cpf = documento_limpo
            cnpj = None

        elif len(documento_limpo) == 14:
            tipo_pessoa = "pj"
            cpf = None
            cnpj = documento_limpo

        else:
            return Response(
                {"error": "Documento inválido. Informe um CPF (11 dígitos) ou CNPJ (14 dígitos)."},
                status=400
            )

        # ==========================================================
        # 🔹 Cria organização com tipo_pessoa + CPF/CNPJ
        # ==========================================================
        try:
            organizacao = Organizacao.objects.create(
                nome=nome_organizacao,
                tipo_pessoa=tipo_pessoa,
                cpf=cpf,
                cnpj=cnpj
            )
        except IntegrityError:
            return Response(
                {"error": "Já existe uma organização com esse nome."},
                status=400
            )

        # Cria usuário admin
        user = CustomUser.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role="admin",
            organizacao=organizacao,
            is_staff=True,
            password=password
        )
        # ==========================================================
        # 🔹 INTEGRAÇÃO ASAAS: Criar cliente
        # ==========================================================
        try:
            provedor = ProvedorPagamento.objects.get(tipo="asaas")

            # AsaasService correto (com os argumentos certos)
            asaas = AsaasService(provedor)

            # Cria cliente no ASAAS
            asaas.criar_cliente(organizacao)

            # Cria assinatura trial local
            asaas.criar_assinatura_trial(organizacao)

        except Exception as e:
            return Response({
                "error": "Organização criada, mas falha ao registrar cliente no ASAAS.",
                "detalhes": str(e)
            }, status=500)
