import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from integracoes.models import GoogleContactsIntegration

class GoogleContactsService:

    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, user):
        self.user = user
        self.integration = GoogleContactsIntegration.objects.get(user=user)

    # ==============================
    # 🔐 TOKEN MANAGEMENT
    # ==============================

    def get_valid_access_token(self):
        """
        Retorna um access_token válido.
        Se estiver expirado, renova automaticamente.
        """
        if self.integration.is_expired():
            self.refresh_access_token()

        return self.integration.access_token

    def refresh_access_token(self):
        """
        Usa refresh_token para gerar novo access_token
        """
        if not self.integration.refresh_token:
            raise Exception("Refresh token não disponível")

        data = {
            "client_id": settings.GOOGLE_CONTACTS_CLIENT_ID,
            "client_secret": settings.GOOGLE_CONTACTS_CLIENT_SECRET,
            "refresh_token": self.integration.refresh_token,
            "grant_type": "refresh_token",
        }

        response = requests.post(self.TOKEN_URL, data=data)
        token_data = response.json()

        if "access_token" not in token_data:
            raise Exception(f"Erro ao renovar token: {token_data}")

        self.integration.access_token = token_data["access_token"]
        self.integration.token_expiry = timezone.now() + timedelta(
            seconds=token_data["expires_in"]
        )

        self.integration.save()

    # ==============================
    # 📇 CONTACTS (vamos usar depois)
    # ==============================

    def fetch_contacts(self, page_token=None, page_size=100):
        """
        Busca contatos do Google People API
        """
        access_token = self.get_valid_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        params = {
            "pageSize": page_size,
            "personFields": "names,emailAddresses,phoneNumbers",
        }

        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            "https://people.googleapis.com/v1/people/me/connections",
            headers=headers,
            params=params,
        )

        return response.json()
