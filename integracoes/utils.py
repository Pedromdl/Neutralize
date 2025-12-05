import time
import requests
from django.conf import settings
from .models import StravaAccount


def get_valid_access_token(user):
    """Retorna sempre um access_token válido (faz refresh quando necessário)."""
    
    try:
        account = user.strava_account
    except StravaAccount.DoesNotExist:
        return None  # usuário não conectou Strava

    # Se o token ainda é válido → retorna
    if account.token_expires_at > int(time.time()):
        return account.access_token

    # Caso contrário, fazer refresh
    refresh_url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": account.refresh_token,
    }

    response = requests.post(refresh_url, data=data)

    if not response.ok:
        print("Erro ao renovar token:", response.text)
        return None

    new_data = response.json()

    # Atualiza no banco
    account.access_token = new_data["access_token"]
    account.refresh_token = new_data["refresh_token"]
    account.token_expires_at = new_data["expires_at"]
    account.save()

    return account.access_token
