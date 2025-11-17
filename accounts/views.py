from django.conf import settings  # importe settings do Django
from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from google.oauth2 import id_token
from google.auth.transport import requests

from .serializers import ClinicaSerializer, CustomUserSerializer, DocumentoLegalSerializer, AceiteDocumentoSerializer
from .models import Clinica, DocumentoLegal, CustomUser
from api.models import Usuário

User = get_user_model()

class CriarClinicaView(generics.CreateAPIView):
    queryset = Clinica.objects.all()
    serializer_class = ClinicaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Cria a clínica
        clinica = serializer.save()

        # Atribui o criador como administrador
        user = self.request.user
        user.clinica = clinica
        user.role = "admin"
        user.is_staff = True
        user.save()

    def create(self, request, *args, **kwargs):
        if request.user.clinica:
            return Response(
                {"detail": "Você já está vinculado a uma clínica."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        print("Usuário autenticado na requisição:", self.request.user)
        return self.request.user

class UserListView(generics.ListAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all().order_by('id')  # Adicione um order_by aqui
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import CustomUser  # seu modelo CustomUser

class GoogleAuthView(APIView):
    """
    Login via Google apenas para usuários existentes.
    Atualiza dados do Google, bloqueia emails não registrados.
    """

    def post(self, request):
        token = request.data.get("token")
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)

        if not client_id:
            return Response(
                {"error": "GOOGLE_CLIENT_ID não configurado no backend"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not token:
            return Response({"error": "Token não enviado"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Valida o token no Google
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)

            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")

            if not email:
                return Response({"error": "E-mail não encontrado no token"}, status=status.HTTP_400_BAD_REQUEST)

            # Procura usuário existente
            try:
                user = CustomUser.objects.get(email=email)

                # Atualiza dados do Google
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.save()

            except CustomUser.DoesNotExist:
                return Response({"error": "Email não registrado no sistema."}, status=status.HTTP_400_BAD_REQUEST)

            # Gera tokens JWT
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            })

        except ValueError as e:
            print("Erro na validação do token:", e)
            return Response({"error": "Token inválido"}, status=status.HTTP_400_BAD_REQUEST)
        
from django.contrib.auth import authenticate

class LoginView(APIView):
    """
    Endpoint para login tradicional com email e senha
    """

    def post(self, request):
        email = request.data.get("email")
        senha = request.data.get("senha")

        if not all([email, senha]):
            return Response({"error": "Email e senha são obrigatórios."}, status=400)

        user = authenticate(request, email=email, password=senha)
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

import random, string


class RegisterAdminClinicaView(APIView):
    """
    Cria uma clínica e um CustomUser administrador a partir do email e nome da clínica.
    """

    def post(self, request):
        email = request.data.get("email")
        nome_clinica = request.data.get("nome")

        if not all([email, nome_clinica]):
            return Response({"error": "Nome da clínica e email são obrigatórios."}, status=400)

        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "Email já cadastrado."}, status=400)

        # Cria a clínica
        clinica = Clinica.objects.create(nome=nome_clinica)

        # Gera uma senha aleatória para o admin
        senha_aleatoria = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # Cria o usuário admin
        user = CustomUser.objects.create_user(
            email=email,
            first_name=nome_clinica,
            role="admin",
            clinica=clinica,
            is_staff=True
        )

        # Cria ou vincula Usuário
        usuario, _ = Usuário.objects.get_or_create(
            email=email,
            defaults={
                "nome": nome_clinica,
                "clinica": clinica,
                "user": user
            }
        )

        # Retorna tokens JWT para login
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        })