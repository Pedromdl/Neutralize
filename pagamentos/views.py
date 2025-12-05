# pagamentos/views.py
from pytz import timezone as pytz_timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from datetime import timedelta, date, datetime
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
import uuid

from accounts.models import Organizacao
from pagamentos.services.asaas_service import AsaasService

from .models import ProvedorPagamento, PlanoPagamento, Assinatura, TransacaoPagamento, WebhookLog

# -------------------------
# Views públicas
# -------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_planos(request):
    """API: Lista planos disponíveis (para React)"""
    planos = PlanoPagamento.objects.filter(ativo=True)

    planos_data = []
    for plano in planos:
        planos_data.append({
            'id': plano.id,
            'nome': plano.nome,
            'tipo': plano.tipo,
            'preco_mensal': float(plano.preco_mensal),
            'descricao': plano.descricao,
            'max_pacientes': plano.max_pacientes,
            'max_usuarios': plano.max_usuarios,
            'max_avaliacoes_mes': plano.max_avaliacoes_mes,
            'dias_trial': plano.dias_trial,
            'recursos': plano.recursos
        })

    return Response({'planos': planos_data})

    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalhes_assinatura(request, assinatura_id=None):
    """API: Detalhes da assinatura (para React)"""
    try:
        organizacao = request.user.organizacao  # 🔥 já temos a organização aqui

        if assinatura_id:
            assinatura = get_object_or_404(
                Assinatura,
                id=assinatura_id,
                organizacao=organizacao
            )
        else:
            assinaturas = Assinatura.objects.filter(organizacao=organizacao)

            assinatura = (
                assinaturas.filter(status="ativa").order_by('-id').first()
                or assinaturas.order_by('-id').first()
            )

            if not assinatura:
                return Response({
                    'assinatura': None,
                    'message': 'Nenhuma assinatura encontrada para esta organização',
                    'organizacao': {
                        "id": organizacao.id,
                        "nome": organizacao.nome,
                        "credit_card_token": organizacao.credit_card_token
                    }
                })

        hoje = timezone.now().date()

        # 🔥 Atualiza trial expirado → aguardando_pagamento
        if assinatura.data_fim_trial and assinatura.data_fim_trial.date() < hoje:
            if assinatura.status == "trial":
                assinatura.status = "aguardando_pagamento"
                assinatura.save()

        # Transações
        transacoes = assinatura.transacoes.all().order_by('-data_criacao')

        transacoes_data = []
        for transacao in transacoes:
            transacoes_data.append({
                'id': transacao.id_transacao_externo,
                'valor': float(transacao.valor),
                'status': transacao.status,
                'data_vencimento': transacao.data_vencimento.isoformat(),
                'data_pagamento': transacao.data_pagamento.isoformat() if transacao.data_pagamento else None,
                'metodo_pagamento': transacao.metodo_pagamento,
                'url_boleto': transacao.url_boleto,
                'codigo_pix': transacao.codigo_pix,
                'qrcode_pix': transacao.qrcode_pix,
            })

        # 🔥 RETORNO COMPLETO
        return Response({
            'organizacao': {
                "id": organizacao.id,
                "nome": organizacao.nome,
                "credit_card_token": organizacao.credit_card_token  # 🔥 necessário para ativar assinatura
            },
            'assinatura': {
                'id': assinatura.id,
                'plano': {
                    'nome': assinatura.plano.nome,
                    'preco_mensal': float(assinatura.plano.preco_mensal),
                    'max_pacientes': assinatura.plano.max_pacientes,
                    'max_usuarios': assinatura.plano.max_usuarios,
                    'max_avaliacoes_mes': assinatura.plano.max_avaliacoes_mes,
                },
                'status': assinatura.status,
                'status_display': assinatura.get_status_display(),
                'metodo_pagamento': assinatura.metodo_pagamento,
                'metodo_pagamento_display': assinatura.get_metodo_pagamento_display() if assinatura.metodo_pagamento else None,
                'data_inicio': assinatura.data_inicio.isoformat(),
                'data_proximo_pagamento': assinatura.data_proximo_pagamento.isoformat() if assinatura.data_proximo_pagamento else None,
                'em_trial': assinatura.em_trial,
                'data_fim_trial': assinatura.data_fim_trial.isoformat() if assinatura.data_fim_trial else None,
                'id_assinatura_externo': assinatura.id_assinatura_externo
            },
            'transacoes': transacoes_data
        })

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ativar_assinatura_com_cartao(request, assinatura_id):
    try:
        user = request.user
        org = user.organizacao

        try:
            assinatura = Assinatura.objects.get(id=assinatura_id, organizacao=org)
        except Assinatura.DoesNotExist:
            return Response(
                {"error": "Assinatura não encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 🔥 Só pode ativar se estiver aguardando pagamento
        if assinatura.status != "aguardando_pagamento":
            return Response(
                {"error": "A assinatura não está em estado válido para ativação."},
                status=status.HTTP_400_BAD_REQUEST
            )

        dados_cartao = request.data.get("dados_cartao", {})
        holder_info = request.data.get("holder_info", {})

        # 🔥 LOG para investigar
        print("RAW REQUEST DATA:", request.data)
        print("DADOS CARTAO:", dados_cartao)
        print("HOLDER INFO:", holder_info)

        # 🔥 Validações simples
        required_card = ["holderName", "number", "expiryMonth", "expiryYear", "ccv"]
        required_holder = ["name", "email", "cpfCnpj", "postalCode", "addressNumber", "phone", "remoteIp"]

        for key in required_card:
            if key not in dados_cartao:
                return Response({"error": f"Campo obrigatório ausente: {key}"}, status=400)

        for key in required_holder:
            if key not in holder_info:
                return Response({"error": f"Campo obrigatório ausente: {key}"}, status=400)

        # 🔥 Instancia o ASAAS Service
        provedor = ProvedorPagamento.objects.first()
        asaas = AsaasService(provedor)

        customer_id = org.asaas_customer_id
        valor = float(assinatura.plano.preco_mensal)
        due_date = timezone.now().date().isoformat()
        external_id = f"assinatura_org_{org.id}"

        # 🔥 CHAMADA CORRETA
        asaas_resposta = asaas.criar_assinatura_com_cartao(
            organizacao=org,
            customer_id=customer_id,
            valor=valor,
            due_date=due_date,
            card_data=dados_cartao,
            holder_info=holder_info,
            external_id=external_id
        )

        print("ASAAS RESPONSE:", asaas_resposta)

        # 🔥 Checa erros do ASAAS
        if "errors" in asaas_resposta:
            msg = asaas_resposta["errors"][0].get("description", "Erro desconhecido no Asaas.")
            return Response({"error": msg}, status=400)

        if "id" not in asaas_resposta:
            return Response({"error": "Resposta inesperada do Asaas."}, status=400)

        # 🔥 Atualiza assinatura
        assinatura.status = "ativa"
        assinatura.metodo_pagamento = "cartao"
        assinatura.id_assinatura_externo = asaas_resposta["id"]
        assinatura.data_proximo_pagamento = asaas_resposta.get("nextDueDate", due_date)
        assinatura.save()

        # 🔥 Registra a transação
        if "charge" in asaas_resposta:
            charge = asaas_resposta["charge"]

            TransacaoPagamento.objects.create(
                assinatura=assinatura,
                id_transacao_externo=charge["id"],
                valor=charge["value"],
                status=charge["status"],
                data_vencimento=charge["dueDate"],
                metodos_pagamento="cartao",
                data_pagamento=charge.get("confirmedDate")
            )

        return Response({
            "success": True,
            "assinatura": {
                "id": assinatura.id,
                "status": assinatura.status,
                "metodo_pagamento": assinatura.metodo_pagamento,
                "data_proximo_pagamento": assinatura.data_proximo_pagamento,
            }
        })

    except Exception as e:
        print("ERRO AO ATIVAR ASSINATURA:", str(e))
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import time  # Adicione no topo do arquivo
from django.utils import timezone
from datetime import timedelta

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ativar_assinatura_usando_token(request, assinatura_id):
    """
    Cria uma nova assinatura usando o credit_card_token salvo na Organização.
    Não exige dados do cartão no frontend.
    Útil quando o cliente já cancelou a assinatura anterior e quer gerar uma nova.
    """
    try:
        user = request.user
        organizacao = user.organizacao

        # Busca a assinatura antiga para referência do plano
        try:
            assinatura_antiga = Assinatura.objects.get(id=assinatura_id, organizacao=organizacao)
        except Assinatura.DoesNotExist:
            return Response({"error": "Assinatura não encontrada."}, status=404)

        # Verifica se a organização tem cartão salvo
        if not organizacao.credit_card_token:
            return Response({"error": "Nenhum cartão salvo. Faça o pagamento usando cartão primeiro."}, status=400)

        # Busca provedor ASAAS
        provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()
        if not provedor:
            return Response({"error": "Provedor ASAAS não configurado."}, status=500)

        # Pega plano da assinatura antiga
        plano = assinatura_antiga.plano
        if not plano:
            return Response({"error": "Assinatura sem plano associado."}, status=400)

        # Instancia o serviço ASAAS
        asaas = AsaasService(provedor)

        # External ID único
        external_id = f"assinatura_org_{organizacao.id}_{int(timezone.now().timestamp())}"

        # Chamada ASAAS usando token
        asaas_resposta = asaas.criar_assinatura_com_token(
            organizacao=organizacao,
            customer_id=organizacao.asaas_customer_id,
            valor=float(plano.preco_mensal),
            due_date=timezone.now().date().isoformat(),
            credit_card_token=organizacao.credit_card_token,
            holder_info={"remoteIp": "127.0.0.1"},
            external_id=external_id
        )

        print("💡 ASAAS RESPONSE:", asaas_resposta)

        # Checa erros do ASAAS
        if "errors" in asaas_resposta:
            msg = asaas_resposta["errors"][0].get("description", "Erro desconhecido no ASAAS.")
            return Response({"error": msg}, status=400)

        if "id" not in asaas_resposta:
            return Response({"error": "Resposta inesperada do ASAAS."}, status=400)

        # Cria nova assinatura local
        nova_assinatura = Assinatura.objects.create(
            organizacao=organizacao,
            plano=plano,
            provedor=provedor,
            status="ativa",
            metodo_pagamento="cartao",
            id_assinatura_externo=asaas_resposta["id"],
            data_proximo_pagamento=asaas_resposta.get("nextDueDate", timezone.now() + timedelta(days=30))
        )

        print(f"💾 Nova assinatura criada: {nova_assinatura.id}")

        # ============================================================
        # BUSCA COBRANÇAS NO ASAAS COM DELAY
        # ============================================================
        subscription_id = asaas_resposta["id"]
        print(f"🔍 Buscando cobranças para assinatura: {subscription_id}")
        
        # Pequeno delay para garantir que o ASAAS processou a cobrança
        print("⏳ Aguardando 3 segundos para processamento do ASAAS...")
        time.sleep(3)  # Aguarda 3 segundos
        
        cobrancas_data = asaas.buscar_cobrancas_associadas(subscription_id)
        
        # Se não encontrou, tenta mais uma vez após outro delay
        if not cobrancas_data or not cobrancas_data.get("data"):
            print("⏳ Tentativa 2: Aguardando mais 2 segundos...")
            time.sleep(2)
            cobrancas_data = asaas.buscar_cobrancas_associadas(subscription_id)
        
        if cobrancas_data and cobrancas_data.get("data"):
            print(f"✅ Encontradas {len(cobrancas_data['data'])} cobrança(s)")
            
            for cobranca in cobrancas_data["data"]:
                # Usa get_or_create para evitar duplicação
                transacao, created = TransacaoPagamento.objects.get_or_create(
                    id_transacao_externo=cobranca["id"],
                    defaults={
                        "assinatura": nova_assinatura,
                        "valor": cobranca["value"],
                        "status": cobranca["status"],
                        "data_vencimento": cobranca["dueDate"],
                        "metodo_pagamento": "cartao",
                        "data_pagamento": cobranca.get("confirmedDate")
                    }
                )
                
                if created:
                    print(f"💾 Transação criada: {cobranca['id']} (status: {cobranca['status']})")
                else:
                    print(f"⚠️ Transação já existia: {cobranca['id']}")
        else:
            print("⚠️ Nenhuma cobrança encontrada no ASAAS após tentativas")
            
            # Fallback: Cria transação básica mesmo sem cobrança do ASAAS
            TransacaoPagamento.objects.create(
                assinatura=nova_assinatura,
                id_transacao_externo=f"sub_{subscription_id}_pending",
                valor=float(plano.preco_mensal),
                status="pending",
                data_vencimento=timezone.now().date(),
                metodos_pagamento="cartao",
                observacoes="Aguardando sincronização com ASAAS"
            )
            print(f"💾 Transação fallback criada para assinatura {nova_assinatura.id}")

        # ============================================================
        # (OPCIONAL) Mantém o código original para charge direto na resposta
        # ============================================================
        charge = asaas_resposta.get("charge")
        if charge:  # Se veio charge na resposta, cria/atualiza
            transacao, created = TransacaoPagamento.objects.update_or_create(
                id_transacao_externo=charge["id"],
                defaults={
                    "assinatura": nova_assinatura,
                    "valor": charge["value"],
                    "status": charge["status"],
                    "data_vencimento": charge["dueDate"],
                    "metodos_pagamento": "cartao",
                    "data_pagamento": charge.get("confirmedDate")
                }
            )
            
            if created:
                print(f"💾 Transação criada via charge direto: {charge['id']}")
            else:
                print(f"📝 Transação atualizada via charge direto: {charge['id']}")

        return Response({
            "success": True,
            "assinatura": {
                "id": nova_assinatura.id,
                "status": nova_assinatura.status,
                "metodo_pagamento": nova_assinatura.metodo_pagamento,
                "data_proximo_pagamento": nova_assinatura.data_proximo_pagamento,
            },
            "transacoes_criadas": TransacaoPagamento.objects.filter(assinatura=nova_assinatura).count()
        })

    except Exception as e:
        print("🚨 ERRO AO ATIVAR ASSINATURA:", str(e))
        return Response({"error": str(e)}, status=500)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancelar_assinatura(request, assinatura_id):
    """Cancela uma assinatura tanto no ASAAS quanto localmente."""
    try:
        assinatura = get_object_or_404(
            Assinatura,
            id=assinatura_id,
            organizacao=request.user.organizacao
        )

        # ================================
        # 1. Cancela no ASAAS primeiro
        # ================================
        if assinatura.id_assinatura_externo:
            provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()
            service = AsaasService(provedor)

            try:
                resp = service.cancelar_assinatura_asaas(assinatura.id_assinatura_externo)
            except Exception as e:
                return Response({
                    'success': False,
                    'error': f'Erro ao cancelar no ASAAS: {str(e)}'
                }, status=400)

        # ================================
        # 2. Cancela localmente
        # ================================
        assinatura.status = 'cancelada'
        assinatura.data_cancelamento = timezone.now()
        assinatura.save()

        # ================================
        # 3. Cancela cobranças pendentes
        # ================================
        assinatura.transacoes.filter(status='pending').update(status='cancelled')

        return Response({
            'success': True,
            'message': 'Assinatura cancelada com sucesso.'
        })

    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=400)


# -------------------------
# Webhook (sem autenticação)
# -------------------------
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@api_view(['POST'])
def webhook_asaas(request):
    """
    Webhook consolidado do ASAAS para:
    - Registrar logs
    - Reconciliar transações automaticamente
    - Interpretar corretamente TODAS as cobranças da assinatura
    - Atualizar assinatura e transações locais
    """
    webhook_log = None
    
    try:
        payload = request.data
        provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()

        evento = payload.get('event') or payload.get('type') or 'unknown'

        # Extração genérica do bloco principal
        transacao_info = (
            payload.get('payment') or
            payload.get('transaction') or
            payload.get('data') or
            payload
        )

        if not isinstance(transacao_info, dict):
            transacao_info = {}

        # campos principais
        external_id = (
            transacao_info.get('id')
            or transacao_info.get('transactionId')
            or transacao_info.get('chargeId')
        )

        # 🔥 1. Registrar o webhook INICIAL (ainda não processado)
        webhook_log = WebhookLog.objects.create(
            provedor=provedor,
            payload=payload,
            evento=evento,
            id_externo=external_id or '',
            processado=False,
            erro=''
        )

        print(f"📥 Webhook recebido: {evento} - ID: {external_id}")

        try:
            # ============================================================
            # SEU CÓDIGO DE PROCESSAMENTO ORIGINAL (mantido intacto)
            # ============================================================
            
            # mapa de status
            status_map = {
                'PAID': 'received',
                'CONFIRMED': 'confirmed',
                'PENDING': 'pending',
                'OVERDUE': 'overdue',
                'REFUNDED': 'refunded',
                'CANCELLED': 'cancelled'
            }

            raw_status = transacao_info.get('status', '').upper()
            mapped_status = status_map.get(raw_status, "pending")

            # tentamos localizar transação existente
            tx = None
            if external_id:
                tx = TransacaoPagamento.objects.filter(id_transacao_externo=external_id).first()

            # -------------------------------------------------------------
            # UTILITÁRIOS DE DATA
            # -------------------------------------------------------------
            from datetime import datetime, date

            def parse_date_only(value):
                if not value:
                    return None
                if isinstance(value, date) and not isinstance(value, datetime):
                    return value
                try:
                    return datetime.fromisoformat(value).date()
                except:
                    try:
                        return date.fromisoformat(value)
                    except:
                        return timezone.now().date()

            def parse_datetime(value):
                if not value:
                    return None
                try:
                    return datetime.fromisoformat(value)
                except:
                    return timezone.now()

            # -------------------------------------------------------------
            # ENCONTRAR A ASSINATURA (VERSÃO ROBUSTA)
            # -------------------------------------------------------------
            assinatura = None

            # 1) subscriptionId
            subscription_id = (
                transacao_info.get('subscription')
                or transacao_info.get('subscriptionId')
                or transacao_info.get('externalReference')
            )

            if subscription_id and not assinatura:
                assinatura = Assinatura.objects.filter(id_assinatura_externo=subscription_id).first()

            # 2) customer → assinatura
            customer_id = transacao_info.get('customer')
            if customer_id and not assinatura:
                assinatura = Assinatura.objects.filter(id_cliente_externo=customer_id).first()

            # 3) Reconciliação: achar pela última transação da mesma organização
            if not assinatura and external_id:
                prev_tx = TransacaoPagamento.objects.filter(
                    dados_transacao__value=transacao_info.get("value")
                ).order_by('-id').first()

                if prev_tx:
                    assinatura = prev_tx.assinatura

            # 4) fallback total — assinatura ativa (se só houver uma)
            if not assinatura:
                assinatura = Assinatura.objects.filter(status="ativa").first()

            # -------------------------------------------------------------
            # SE A TRANSAÇÃO AINDA NÃO EXISTE → CRIA
            # -------------------------------------------------------------
            if not tx and external_id:
                valor = transacao_info.get("value") or transacao_info.get("amount") or 0

                due_raw = (transacao_info.get("dueDate")
                           or transacao_info.get("originalDueDate")
                           or transacao_info.get("dateCreated"))

                due_date = parse_date_only(due_raw)

                data_pagamento = None
                if mapped_status in ('received', 'confirmed'):
                    data_pagamento = parse_datetime(
                        transacao_info.get("paymentDate")
                        or transacao_info.get("confirmedDate")
                        or transacao_info.get("clientPaymentDate")
                    )

                tx = TransacaoPagamento.objects.create(
                    assinatura=assinatura,
                    id_transacao_externo=external_id,
                    valor=valor,
                    data_vencimento=due_date,
                    data_pagamento=data_pagamento,
                    status=mapped_status,
                    metodo_pagamento=transacao_info.get("billingType"),
                    dados_transacao=transacao_info
                )

                print(f"🔥 Transação criada: {external_id}")

            # -------------------------------------------------------------
            # ATUALIZA TRANSAÇÃO EXISTENTE
            # -------------------------------------------------------------
            if tx:
                tx.status = mapped_status

                if mapped_status in ('received', 'confirmed'):
                    tx.data_pagamento = timezone.now()

                tx.dados_transacao['webhook_payload'] = json.loads(json.dumps(transacao_info))
                tx.save()

            # -------------------------------------------------------------
            # ATUALIZAR ASSINATURA
            # -------------------------------------------------------------
            if assinatura:
                if mapped_status in ('pending',):
                    if assinatura.status not in ('cancelada', 'suspensa'):
                        assinatura.status = 'aguardando_pagamento'

                elif mapped_status in ('overdue',):
                    assinatura.status = 'suspensa'

                elif mapped_status in ('received', 'confirmed'):
                    assinatura.status = 'ativa'
                    assinatura.data_proximo_pagamento = parse_date_only(transacao_info.get("nextDueDate"))
                elif mapped_status in ('cancelled',):
                    assinatura.status = 'cancelada'

                assinatura.save()
                print(f"✅ Assinatura atualizada: {assinatura.id} → {assinatura.status}")

            # 🔥 2. SE CHEGOU AQUI SEM ERROS = SUCESSO!
            webhook_log.processado = True
            webhook_log.save()
            
            print(f"✅ Webhook processado com sucesso: {evento}")
            return Response({"status": "success"})

        except Exception as e:
            # 🔥 3. ERRO DURANTE PROCESSAMENTO (salva no log)
            error_msg = str(e)
            print(f"❌ ERRO NO PROCESSAMENTO DO WEBHOOK: {error_msg}")
            
            if webhook_log:
                webhook_log.erro = error_msg
                webhook_log.save()
            
            # Re-lançar o erro para retornar 400
            raise

    except Exception as e:
        # 🔥 4. ERRO GERAL (antes/durante criação do log)
        error_msg = str(e)
        print(f"❌ ERRO GRAVE NO WEBHOOK: {error_msg}")
        
        # Se webhook_log foi criado mas ainda não tem erro, atualizar
        if webhook_log and not webhook_log.erro:
            webhook_log.erro = error_msg
            webhook_log.save()
        
        return Response(
            {"status": "error", "detail": error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )