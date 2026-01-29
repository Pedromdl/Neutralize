import os
from django.shortcuts import redirect
import time
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from urllib.parse import urlencode

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import requests
import secrets

from .models import StravaAccount, GoogleContactsIntegration

from .utils import get_valid_access_token

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import os
from dotenv import load_dotenv


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
    return redirect(f"http://localhost:5173/integracoes?strava_connected=1")



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

# ------------------------------------------------------------------
# INÍCIO DO FLUXO OAUTH
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def google_contacts_connect(request):
    """
    Inicia o fluxo OAuth para Google Contacts usando state para identificar usuário.
    """

    # 🔐 token aleatório para proteger o state
    random_token = secrets.token_urlsafe(16)

    # Aqui pegamos o user_id via query param, porque request.user NÃO funciona com AllowAny
    # Ou você poderia passar o JWT e decodificar
    user_token = request.GET.get("token")
    if not user_token:
        return JsonResponse({"error": "token missing"}, status=400)

    # Você precisaria decodificar o JWT para pegar user_id
    import jwt
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        payload = jwt.decode(user_token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload["user_id"]
    except Exception:
        return JsonResponse({"error": "invalid token"}, status=401)

    # state = "userID:randomToken"
    state = f"{user_id}:{random_token}"

    # opcional: salvar só o random token na sessão pra validar depois
    request.session["google_contacts_oauth_state_token"] = random_token

    params = {
        "client_id": settings.GOOGLE_CONTACTS_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_CONTACTS_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/contacts.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }

    oauth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return redirect(oauth_url)


# ------------------------------------------------------------------
# CALLBACK DO GOOGLE
# ------------------------------------------------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def google_contacts_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")  # vem como "userID:randomToken"

    if not code or not state:
        return JsonResponse({"error": "missing code or state"}, status=400)

    try:
        user_id_str, random_token = state.split(":")
        user_id = int(user_id_str)
    except Exception:
        return JsonResponse({"error": "invalid state"}, status=400)

    # ✅ validar token aleatório com o que está salvo na sessão
    saved_token = request.session.get("google_contacts_oauth_state_token")
    if saved_token != random_token:
        return JsonResponse({"error": "invalid oauth state"}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "user not found"}, status=404)

    # continua o fluxo normal: trocar code por access_token e salvar no banco

    # -----------------------------
    # 4. Troca code por tokens
    # -----------------------------
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "client_id": settings.GOOGLE_CONTACTS_CLIENT_ID,
        "client_secret": settings.GOOGLE_CONTACTS_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_CONTACTS_REDIRECT_URI,
    }

    response = requests.post(
        token_url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )

    token_data = response.json()

    if "access_token" not in token_data:
        return redirect(
            f"{settings.FRONTEND_URL}/integracoes?google_connected=1"
        )
    # -----------------------------
    # 5. Calcula expiração do token
    # -----------------------------
    expires_at = timezone.now() + timedelta(
        seconds=token_data["expires_in"]
    )

    # -----------------------------
    # 6. Salva / atualiza integração
    # -----------------------------
    GoogleContactsIntegration.objects.update_or_create(
        user=user,
        defaults={
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_expiry": expires_at,
            "scope": token_data.get("scope"),
        }
    )

    # -----------------------------
    # 7. Limpa dados sensíveis da sessão
    # -----------------------------
    request.session.pop("google_contacts_oauth_state", None)
    request.session.pop("google_contacts_user_id", None)

    return redirect(f"{settings.FRONTEND_URL}/integracoes?google_connected=1")

from .services.google_contacts import GoogleContactsService

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def google_contacts_list(request):
    """
    Retorna contatos do Google com paginação
    """
    try:
        page_token = request.GET.get("page_token")

        service = GoogleContactsService(request.user)
        data = service.fetch_contacts(page_token=page_token)

        return Response({
            "connections": data.get("connections", []),
            "nextPageToken": data.get("nextPageToken"),
        })

    except GoogleContactsIntegration.DoesNotExist:
        return Response(
            {"error": "Conta Google não conectada"},
            status=400
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=500
        )
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def google_contacts_disconnect(request):
    try:
        integration = GoogleContactsIntegration.objects.get(user=request.user)

        # 🔒 (Opcional, recomendado) Revogar token no Google
        if integration.access_token:
            try:
                requests.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": integration.access_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=5,
                )
            except Exception:
                pass  # falha na revogação não deve quebrar o fluxo

        # 🗑 Remove integração local
        integration.delete()

        return Response({"disconnected": True})

    except GoogleContactsIntegration.DoesNotExist:
        return Response({"disconnected": False, "detail": "Conta Google não conectada"})
    
class GoogleContactsStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        integration = GoogleContactsIntegration.get_for_user(request.user)

        if not integration:
            return Response({
                "conectado": False
            })

        # opcional: considerar token expirado como desconectado
        if integration.is_expired():
            return Response({
                "conectado": False,
                "motivo": "token_expirado"
            })

        return Response({
            "conectado": True
        })
    





# INTEGRAÇÃO INSTAGRAM

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
