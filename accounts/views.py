from django.conf import settings  # importe settings do Django
from rest_framework import generics, permissions
from django.contrib.auth import get_user_model
from .serializers import CustomUserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()

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

class GoogleAuthView(APIView):

    def post(self, request):
        token = request.data.get("token")
        client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)

        print("GOOGLE_CLIENT_ID no backend:", client_id)
        print("Token recebido:", token)

        if not client_id:
            return Response(
                {"error": "GOOGLE_CLIENT_ID não configurado no backend"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not token:
            return Response({"error": "Token não enviado"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Valida o token no Google
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                client_id
            )

            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")

            if not email:
                return Response({"error": "E-mail não encontrado no token"}, status=status.HTTP_400_BAD_REQUEST)

            # Cria ou obtém o usuário
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"first_name": first_name, "last_name": last_name}
            )

            # Gera tokens JWT
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            })

        except ValueError as e:
            print("Erro na validação do token:", e)
            return Response({"error": "Token inválido"}, status=status.HTTP_400_BAD_REQUEST)
