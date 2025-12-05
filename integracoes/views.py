import os
from django.shortcuts import redirect
import time
from datetime import datetime, timezone
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import requests
from .models import StravaAccount

from .utils import get_valid_access_token


STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

@api_view(["GET"])
@permission_classes([AllowAny])
def strava_authorize(request):
    client_id = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri = f"{os.getenv('BACKEND_URL')}/api/strava/callback/"

    auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        "&response_type=code"
        f"&redirect_uri={redirect_uri}"
        "&scope=read,activity:read_all"
    )
    return HttpResponseRedirect(auth_url)
# backend/apps/strava/views.py
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import logging

logger = logging.getLogger(__name__)

# Exemplo de modelo (adapte ao seu projeto)
from .models import StravaAccount
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import redirect
import jwt
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
def strava_callback(request):
    state_token = request.GET.get("state")  # <-- o token enviado do frontend

    # 1️⃣ Decodifica o token para pegar o usuário
    try:
        payload = jwt.decode(state_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        user = User.objects.get(id=user_id)
    except Exception as e:
        return Response({"error": "Token inválido"}, status=400)

    # 2️⃣ Pega o code do Strava
    code = request.GET.get("code")
    if not code:
        return Response({"error": "Código não fornecido"}, status=400)

    # 3️⃣ Troca o code pelo access token do Strava
    import requests
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": settings.STRAVA_CLIENT_ID,
            "client_secret": settings.STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }
    )
    data = response.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_at = data.get("expires_at")
    athlete = data.get("athlete")

    # 4️⃣ Salva os tokens no banco associados ao usuário
    from .models import StravaAccount
    strava_account, created = StravaAccount.objects.update_or_create(
        user=user,
        defaults={
            "strava_id": athlete.get("id"),
            "firstname": athlete.get("firstname"),
            "lastname": athlete.get("lastname"),
            "profile_url": athlete.get("profile"),
            "city": athlete.get("city"),
            "country": athlete.get("country"),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": expires_at,
        }
    )


    # 5️⃣ Redireciona de volta para o frontend
    return redirect(f"http://localhost:5173/paciente/integracoes?strava_connected=1")



# 🔹 Função auxiliar para renovar o token automaticamente
def refresh_strava_token(refresh_token):
    print("🔄 Solicitando novo token ao Strava...")
    url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(url, data=data)
    return response.json()




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def strava_status(request):
    print("🔹 Iniciando Strava Status")

    conta = getattr(request.user, "strava_account", None)
    print("Conta Strava encontrada:", conta)

    if not conta:
        return Response({"conectado": False, "mensagem": "Nenhuma conta conectada."})

    # Converte token_expires_at para datetime se for int (timestamp)
    token_expires = (
        datetime.fromtimestamp(conta.token_expires_at, tz=timezone.utc)
        if isinstance(conta.token_expires_at, int)
        else conta.token_expires_at
    )
    print("Token expirado?", token_expires < datetime.now(timezone.utc))

    if token_expires < datetime.now(timezone.utc):
        print("🔄 Token expirado, fazendo refresh...")
        refresh_url = "https://www.strava.com/oauth/token"
        refresh_data = {
            "client_id": os.getenv("STRAVA_CLIENT_ID"),
            "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
            "grant_type": "refresh_token",
            "refresh_token": conta.refresh_token,
        }
        r = requests.post(refresh_url, data=refresh_data)
        print("Resposta do refresh:", r.status_code, r.text)

        if r.status_code == 200:
            new_tokens = r.json()
            conta.access_token = new_tokens.get("access_token")
            conta.refresh_token = new_tokens.get("refresh_token")
            conta.token_expires_at = datetime.fromtimestamp(
                new_tokens.get("expires_at"), tz=timezone.utc
            )
            conta.save()
            print("Tokens atualizados com sucesso")
        else:
            return Response({"conectado": False, "mensagem": "Falha ao atualizar token Strava."})

    print("🔹 Chamando API do Strava...")
    athlete_res = requests.get(
        "https://www.strava.com/api/v3/athlete",
        headers={"Authorization": f"Bearer {conta.access_token}"}
    )
    print("Status da resposta Strava:", athlete_res.status_code)

    if athlete_res.status_code != 200:
        print("Erro ao buscar dados do atleta:", athlete_res.text)
        return Response({
            "conectado": False,
            "mensagem": f"Erro Strava: {athlete_res.status_code} {athlete_res.text}"
        }, status=athlete_res.status_code)

    athlete_data = athlete_res.json()
    print("Dados do atleta recebidos:", athlete_data)

    return Response({
        "conectado": True,
        "firstname": athlete_data.get("firstname"),
        "lastname": athlete_data.get("lastname"),
        "city": athlete_data.get("city"),
        "country": athlete_data.get("country"),
        "profile": athlete_data.get("profile"),
        "id": athlete_data.get("id"),
    })
# 🔹 Busca atividades (com refresh automático se token expirou)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def strava_atividades(request):
    """Lista as atividades do usuário (com refresh automático de token)."""

    token = get_valid_access_token(request.user)

    if not token:
        return Response(
            {"error": "Strava não está conectado ou houve erro ao renovar token."},
            status=400
        )

    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)

    if not response.ok:
        return Response(
            {"error": "Erro ao acessar atividades da Strava", "details": response.json()},
            status=response.status_code
        )

    return Response(response.json())





# INTEGRAÇÃO INSTAGRAM

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import os
from dotenv import load_dotenv

# Carrega o .env
load_dotenv()  # só precisa se não estiver carregando em settings.py

class InstagramFeedView(APIView):
    def get(self, request):
        instagram_user_id = os.getenv("INSTAGRAM_USER_ID")
        access_token = os.getenv("INSTAGRAM_LONG_TOKEN")

        url = (
            f"https://graph.facebook.com/v21.0/{instagram_user_id}/media"
            "?fields=id,media_url,media_type,thumbnail_url,caption,permalink"
            f"&access_token={access_token}"
        )

        response = requests.get(url)
        data = response.json()

        return Response(data)
