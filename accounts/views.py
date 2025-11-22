from django.conf import settings  # importe settings do Django
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import generics, permissions, filters, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import PermissionDenied


from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from api.mixins import ClinicFilterMixin

from .serializers import CustomUserSerializer, DocumentoLegalSerializer, AceiteDocumentoSerializer
from .models import Clinica, DocumentoLegal, CustomUser
from api.models import Usuário

User = get_user_model()

class CustomUserViewSet(ClinicFilterMixin, viewsets.ModelViewSet):
    """
    CRUD completo de CustomUser:
    - create: cria usuário na clínica do admin logado
    - list: lista apenas usuários da clínica
    - retrieve: obtém um usuário específico
    - update/partial_update: editar usuário
    - destroy: deletar usuário
    """

    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CustomUser.objects.all()
    clinica_field = "clinica"  # ESSENCIAL para o filtro automático

    # ----------------------------------------------------------------------

    def perform_create(self, serializer):
        """
        Garante que o usuário criado pertence à mesma clínica do usuário logado.
        Ignora clinica enviada pelo frontend.
        """
        user = self.request.user

        serializer.save(clinica=user.clinica)

    # ----------------------------------------------------------------------

    def perform_destroy(self, instance):
        """
        Impede que alguém delete usuários de outra clínica (segurança extra).
        """
        if instance.clinica != self.request.user.clinica:
            raise PermissionDenied("Você não pode deletar usuários de outra clínica.")
        instance.delete()

    # ----------------------------------------------------------------------

    def perform_update(self, serializer):
        """
        Garante que a edição não troque o usuário de clínica.
        """
        user = self.request.user
        if serializer.instance.clinica != user.clinica:
            raise PermissionDenied("Você não pode editar usuários de outra clínica.")

        serializer.save(clinica=user.clinica)  # força permanência

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        print("Usuário autenticado na requisição:", self.request.user)
        return self.request.user
    
class UserListView(ClinicFilterMixin, generics.ListAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CustomUser.objects.all()
    clinica_field = "clinica"   # <-- ESSENCIAL
    filter_backends = [filters.OrderingFilter]  # <— habilita ordenação
    ordering_fields = ['id', 'first_name', 'email', 'role']   # <— campos liberados
    ordering = ['id']  # ordenação padrão


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
                        clinica=paciente.clinica,
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
    Cria uma clínica e um CustomUser administrador.
    Agora inclui first_name e last_name fornecidos pelo frontend.
    """

    def post(self, request):
        email = request.data.get("email", "").strip()
        nome_clinica = request.data.get("nome", "").strip()
        password = request.data.get("password", "").strip()
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()

        # Validação dos campos obrigatórios
        if not all([email, nome_clinica, password, first_name, last_name]):
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

        # Cria clínica
        try:
            clinica = Clinica.objects.create(nome=nome_clinica)
        except IntegrityError:
            return Response({"error": "Já existe uma clínica com esse nome."}, status=400)

        # Cria usuário admin
        user = CustomUser.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role="admin",
            clinica=clinica,
            is_staff=True,
            password=password
        )

        # Retorna tokens JWT
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "message": "Clínica e administrador criados com sucesso."
        }, status=201)
