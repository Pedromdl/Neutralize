from datetime import timedelta
import requests
from django.utils import timezone
from django.conf import settings
from accounts.models import CustomUser, Organizacao
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

    def criar_cliente(self, organizacao: Organizacao):
        """
        Cria um cliente no ASAAS representando a ORGANIZAÇÃO.
        Agora 100% alinhado com o modelo Organizacao.
        """

        # Já tem cliente ASAAS? Não criar duplicado.
        if organizacao.asaas_customer_id:
            return {
                "status": "already_exists",
                "customer_id": organizacao.asaas_customer_id
            }

        # Pega o admin responsável
        usuario_admin = CustomUser.objects.filter(
            organizacao=organizacao, role="admin"
        ).first()

        if not usuario_admin:
            raise Exception("Nenhum usuário administrador encontrado para esta clínica.")

        # ======================================================
        # 🔹 Pessoa Jurídica (CNPJ)
        # ======================================================
        if organizacao.tipo_pessoa == "pj":
            payload = {
                "name": organizacao.nome,
                "cpfCnpj": organizacao.cnpj,
                "email": usuario_admin.email,
            }

        # ======================================================
        # 🔹 Pessoa Física (CPF)
        # ======================================================
        else:
            cpf = organizacao.cpf or None
            if not cpf:
                raise Exception("Nenhum CPF disponível para criação de cliente PF.")

            payload = {
                "name": organizacao.nome,
                "cpfCnpj": cpf,
                "email": usuario_admin.email,
            }

        # Envia para o ASAAS
        data = self._post("/customers", payload)

        # Salva o ID retornado
        organizacao.asaas_customer_id = data["id"]
        organizacao.save()

        return data
    
    def criar_assinatura_trial(self, organizacao):
        """
        Cria uma assinatura local em período de trial para a organização recém-criada.
        """

        # Escolhe qual plano será o trial (pode alterar aqui depois)
        plano_trial = PlanoPagamento.objects.get(tipo="starter")
        provedor = ProvedorPagamento.objects.get(tipo="asaas")

        assinatura = Assinatura.objects.create(
            organizacao=organizacao,
            plano=plano_trial,
            provedor=provedor,
            status="trial",
            data_inicio=timezone.now(),
            data_fim_trial=timezone.now() + timedelta(days=plano_trial.dias_trial),
            metodo_pagamento=None,  # Sem pagamento ainda
        )

        return assinatura
        
    def criar_assinatura_com_cartao(self, organizacao: Organizacao, customer_id, valor, due_date, card_data, holder_info, external_id):

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
                "phone": holder_info["phone"],
            },

            "remoteIp": holder_info["remoteIp"],
        }

        # 🔥 Chama o ASAAS
        response = requests.post(
            f"{self.base_url}/subscriptions",
            headers=self.headers,
            json=payload,
            timeout=30
        )

        data = response.json()

        # ============================================================
        # 🔥 Se veio token, salvar no modelo Organizacao
        # ============================================================
        try:
            token = data.get("creditCard", {}).get("creditCardToken")
            if token:
                organizacao.credit_card_token = token
                organizacao.save(update_fields=["credit_card_token"])

        except Exception as e:
            # não quebra o fluxo se algo der errado
            print("Erro ao salvar creditCardToken:", e)

        return data

    # Novo método: criar assinatura usando o credit card token
    def criar_assinatura_com_token(self, customer_id, valor, due_date, credit_card_token, holder_info, external_id):
        
        try:
            # -------------------------------
            # 1️⃣ Preparar payload e headers
            # -------------------------------
            payload = {
                "customer": customer_id,
                "billingType": "CREDIT_CARD",
                "value": valor,
                "creditCardToken": credit_card_token,
                "nextDueDate": due_date,
                "cycle": "MONTHLY",
                "description": "Assinatura Neutralize - Mensal",
                "externalReference": external_id,
                "remoteIp": holder_info.get("remoteIp", "")
            }

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "access_token": self.api_key
            }

            # -------------------------------
            # 2️⃣ Log do request
            # -------------------------------
            print("💡 ASAAS - Payload enviado:", payload)
            print("💡 ASAAS - Headers enviados:", headers)

            # -------------------------------
            # 3️⃣ Chamada ASAAS
            # -------------------------------
            response = requests.post(
                f"{self.base_url}/subscriptions",
                json=payload,
                headers=headers,
                timeout=30
            )

            # Checa status HTTP
            response.raise_for_status()

            # -------------------------------
            # 4️⃣ Processa resposta
            # -------------------------------
            try:
                data = response.json()
            except ValueError:
                print("❌ Resposta ASAAS não é JSON:", response.text)
                return {"errors": [{"description": "Resposta ASAAS inválida"}]}

            print("✅ ASAAS RESPONSE:", data)
            return data

        except requests.exceptions.HTTPError as e:
            print("❌ Erro HTTP ASAAS:", e, response.text if 'response' in locals() else "")
            return {"errors": [{"description": f"Erro HTTP ASAAS: {str(e)}"}]}
        except requests.exceptions.RequestException as e:
            print("❌ Erro na requisição ASAAS:", e)
            return {"errors": [{"description": f"Erro na requisição ASAAS: {str(e)}"}]}
        except Exception as e:
            print("❌ Erro inesperado ao criar assinatura com token:", e)
            return {"errors": [{"description": f"Erro inesperado: {str(e)}"}]}

    
    def cancelar_assinatura_asaas(self, subscription_id):
        """Cancela uma assinatura no ASAAS."""
        url = f"{self.base_url}/subscriptions/{subscription_id}"

        response = requests.delete(
            url,
            headers=self.headers,
            timeout=20
        )

        return response.json()
    
    def buscar_cobrancas_associadas(self, subscription_id):
        """Busca todas as cobranças de uma assinatura"""
        try:
            response = requests.get(
                f"{self.base_url}/subscriptions/{subscription_id}/payments",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"❌ Erro ao buscar cobranças: {e}")
            return None
