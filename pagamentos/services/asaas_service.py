import requests
from django.utils import timezone
from django.conf import settings
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
    def criar_cliente(self, assinatura: Assinatura):
        clinica = assinatura.clinica

        payload = {
            "name": clinica.nome,
            "email": clinica.email or clinica.email_contato,
            "phone": clinica.telefone or clinica.whatsapp,
            "cpfCnpj": clinica.cnpj or clinica.cpf,
        }

        data = self._post("/customers", payload)
        assinatura.id_cliente_externo = data["id"]
        assinatura.save()
        return data

    # ================================================
    # 🔹 ASSINATURA RECORRENTE ASAAS
    # ================================================
    def criar_assinatura(self, assinatura: Assinatura):
        if not assinatura.id_cliente_externo:
            raise Exception("Cliente ASAAS não criado.")

        payload = {
            "customer": assinatura.id_cliente_externo,
            "billingType": "UNDEFINED",
            "value": float(assinatura.plano.preco_mensal),
            "cycle": "MONTHLY",
            "description": f"Assinatura {assinatura.plano.nome}",
            "nextDueDate": timezone.now().date().isoformat(),
        }

        data = self._post("/subscriptions", payload)

        assinatura.id_assinatura_externo = data["id"]
        assinatura.save()

        return data

    # ================================================
    # 🔹 REGISTRO DO PAGAMENTO (CARTÃO)
    # ================================================
    def ativar_assinatura_com_cartao(self, assinatura: Assinatura):
        """
        Só funciona se a clínica já mandou o creditCardToken.
        """

        if not assinatura.cartao_token:
            raise Exception("Cartão não registrado.")

        payload = {
            "customer": assinatura.id_cliente_externo,
            "billingType": "CREDIT_CARD",
            "creditCardToken": assinatura.cartao_token,
        }

        data = self._post(f"/subscriptions/{assinatura.id_assinatura_externo}/updateCreditCard", payload)

        return data

    # ================================================
    # 🔹 CANCELAR ASSINATURA
    # ================================================
    def cancelar_assinatura(self, assinatura: Assinatura):
        data = self._delete(f"/subscriptions/{assinatura.id_assinatura_externo}")
        assinatura.status = "cancelada"
        assinatura.data_cancelamento = timezone.now()
        assinatura.save()
        return data

    # ================================================
    # 🔹 TRANSAÇÕES RECEBIDAS PELO WEBHOOK
    # ================================================
    def registrar_transacao(self, assinatura: Assinatura, payload: dict):
        pagamento = payload["payment"]

        trans, _ = TransacaoPagamento.objects.get_or_create(
            id_transacao_externo=pagamento["id"],
            assinatura=assinatura,
            defaults={
                "valor": pagamento["value"],
                "data_vencimento": pagamento["dueDate"],
                "methodo_pagamento": pagamento["billingType"].lower(),
                "dados_transacao": pagamento,
            }
        )

        return trans

    def confirmar_pagamento(self, payload):
        pagamento = payload["payment"]

        try:
            trans = TransacaoPagamento.objects.get(
                id_transacao_externo=pagamento["id"]
            )
        except TransacaoPagamento.DoesNotExist:
            return None

        trans.status = "confirmed"
        trans.data_pagamento = timezone.now()
        trans.save()
        return trans


# =======================================================
# 🔹 FUNÇÃO PRINCIPAL DE ENCAPSULAMENTO (facilidade)
# =======================================================

def get_asaas_service(assinatura: Assinatura):
    return AsaasService(assinatura.provedor)
