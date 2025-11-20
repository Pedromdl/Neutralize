import os
from django.shortcuts import redirect
import time
from datetime import datetime, timezone
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
from .models import StravaAccount

STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")


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


# 🔹 Callback após o login pelo Strava
def strava_callback(request):
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"erro": "Código não encontrado"}, status=400)

    token_url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }

    resp = requests.post(token_url, data=data)
    token_data = resp.json()

    print("✅ Token recebido do Strava:", token_data)

    athlete = token_data.get("athlete", {})
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")

    # 🔸 Converte expires_at (timestamp) para datetime
    expires_at_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)

    # 🔸 Cria ou atualiza conta com base no strava_id
    conta, _ = StravaAccount.objects.update_or_create(
        strava_id=athlete.get("id"),
        defaults={
        "athlete_name": f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}",
        "profile_pic": athlete.get("profile"),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": expires_at_dt,
        },
    )

    return JsonResponse({
        "status": "Conectado com sucesso",
        "athlete": athlete
    })

# 🔹 Retorna status atual da conexão
@api_view(["GET"])
def strava_status(request):
    from .models import StravaAccount
    conta = StravaAccount.objects.first()

    if not conta:
        return Response({"conectado": False, "mensagem": "Nenhuma conta conectada."})

    # Atualiza token se necessário
    from datetime import datetime, timezone
    import requests

    if conta.token_expires_at < datetime.now(timezone.utc):
        refresh_url = "https://www.strava.com/oauth/token"
        refresh_data = {
            "client_id": os.getenv("STRAVA_CLIENT_ID"),
            "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
            "grant_type": "refresh_token",
            "refresh_token": conta.refresh_token,
        }
        r = requests.post(refresh_url, data=refresh_data)
        new_tokens = r.json()
        conta.access_token = new_tokens["access_token"]
        conta.refresh_token = new_tokens["refresh_token"]
        conta.token_expires_at = datetime.fromtimestamp(
            new_tokens["expires_at"], tz=timezone.utc
        )
        conta.save()

    # ✅ Agora busca os dados do atleta
    athlete_res = requests.get(
        "https://www.strava.com/api/v3/athlete",
        headers={"Authorization": f"Bearer {conta.access_token}"}
    )

    athlete_data = athlete_res.json()

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
def strava_atividades(request):
    conta = StravaAccount.objects.first()
    if not conta:
        return Response({"error": "Nenhuma conta Strava conectada."}, status=400)

    now = datetime.now(timezone.utc)

    # Se o token expirou → faz o refresh
    if conta.token_expires_at <= now:
        print("⚠️ Token expirado, renovando...")
        novo_token = refresh_strava_token(conta.refresh_token)
        if "access_token" in novo_token:
            conta.access_token = novo_token["access_token"]
            conta.refresh_token = novo_token.get("refresh_token", conta.refresh_token)
            conta.token_expires_at = datetime.fromtimestamp(novo_token["expires_at"], tz=timezone.utc)
            conta.save()
            print("✅ Token renovado com sucesso!")
        else:
            return Response({"error": "Falha ao renovar token"}, status=401)

    # Faz a chamada real ao Strava
    headers = {"Authorization": f"Bearer {conta.access_token}"}
    res = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers)

    if res.status_code != 200:
        print("❌ Erro ao buscar atividades:", res.text)
        return Response({"error": "Falha ao buscar atividades no Strava."}, status=res.status_code)

    atividades = res.json()
    return Response(atividades)

# 🔹 Redireciona para o login do Strava
def strava_authorize(request):
    client_id = os.getenv("STRAVA_CLIENT_ID"),
    redirect_uri = f"{os.getenv('BACKEND_URL')}/api/strava/callback/"
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope=read,activity:read_all"
    )
    return HttpResponseRedirect(auth_url)


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
