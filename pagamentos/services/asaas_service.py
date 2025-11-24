import requests
from django.utils import timezone
from django.conf import settings
from accounts.models import CustomUser, Clinica
from pagamentos.models import Assinatura, PlanoPagamento, ProvedorPagamento, TransacaoPagamento, WebhookLog




class AsaasService:
    """
    Serviço de integração com o ASAAS.
    Todas as chamadas à API passam por aqui.
    """

    def __init__(self, provedor):
        self.api_key = provedor.api_key
        self.base_url = provedor.base_url
        self.sandbox = provedor.sandbox

        self.headers = {
            "Content-Type": "application/json",
            "access_token": self.api_key
        }

    # ================================================
    # 🔹 CHAMADAS BÁSICAS DE API
    # ================================================
    def _post(self, endpoint, payload):
        url = f"{self.base_url}{endpoint}"
        r = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(r)

    def _get(self, endpoint):
        url = f"{self.base_url}{endpoint}"
        r = requests.get(url, headers=self.headers)
        return self._handle_response(r)

    def _delete(self, endpoint):
        url = f"{self.base_url}{endpoint}"
        r = requests.delete(url, headers=self.headers)
        return self._handle_response(r)

    def _handle_response(self, response):
        """
        Trata erros do ASAAS e retorna JSON limpo.
        """
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()

        if response.status_code >= 400:
            raise Exception(f"Erro ASAAS: {data}")

        return data

    # ================================================
    # 🔹 CLIENTE ASAAS
    # ================================================

    def criar_cliente(self, clinica: Clinica):
        """
        Cria um cliente no ASAAS representando a CLÍNICA.
        A assinatura não deve mais ser responsável por criar clientes.
        """

        # Já existe cliente ASAAS? Evitar duplicação.
        if clinica.asaas_customer_id:
            return {
                "status": "already_exists",
                "customer_id": clinica.asaas_customer_id
            }

        # 🔎 Buscar administrador da clínica (usado para PF)
        usuario_admin = CustomUser.objects.filter(
            clinica=clinica,
            role="admin"
        ).first()

        if not usuario_admin:
            raise Exception("Nenhum usuário administrador encontrado para esta clínica.")

        # ==========================================================
        # 🔹 SE O CLIENTE É PJ → usar CNPJ
        # ==========================================================
        if clinica.cnpj:
            payload = {
                "name": clinica.nome,
                "cpfCnpj": clinica.cnpj,
                "email": usuario_admin.email,       # Email do responsável é válido
                "phone": clinica.telefone or usuario_admin.telefone,
            }

        # ==========================================================
        # 🔹 SE O CLIENTE É PF → usar dados do admin
        # ==========================================================
        else:
            payload = {
                "name": usuario_admin.get_full_name(),
                "cpfCnpj": usuario_admin.cpf,
                "email": usuario_admin.email,
                "phone": usuario_admin.telefone,
            }

        # ==========================================================
        # 🔥 Envia criação ao ASAAS
        # ==========================================================
        data = self._post("/customers", payload)

        # 🔗 Salvar no modelo Clinica
        clinica.asaas_customer_id = data["id"]
        clinica.save()

        return data
    
    def criar_assinatura_com_cartao(self, customer_id, valor, due_date, card_data, holder_info, external_id):
        payload = {
            "customer": customer_id,
            "billingType": "CREDIT_CARD",
            "value": valor,
            "nextDueDate": due_date,
            "cycle": "MONTHLY",
            "description": "Assinatura Neutralize - Mensal",
            "externalReference": external_id,
                "creditCard": {
                "holderName": card_data["holderName"],
                "number": card_data["number"],
                "expiryMonth": card_data["expiryMonth"],
                "expiryYear": card_data["expiryYear"],
                "ccv": card_data["ccv"],
            },
            "creditCardHolderInfo": {
                "name": holder_info["name"],
                "email": holder_info["email"],
                "cpfCnpj": holder_info["cpfCnpj"],
                "postalCode": holder_info["postalCode"],
                "addressNumber": holder_info["addressNumber"],
                "addressComplement": holder_info.get("addressComplement", ""),
                "phone": holder_info["phone"],            },
            "remoteIp": holder_info["remoteIp"],
        }

        r = requests.post(
            f"{self.base_url}/subscriptions",
            headers=self.headers,
            json=payload
        )

        return r.json()
