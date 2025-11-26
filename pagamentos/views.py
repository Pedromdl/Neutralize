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



class CriarAssinaturaClinicaView(APIView):
    """
    Cria a assinatura da organização e salva o creditCardToken no banco
    """

    def post(self, request):
        organizacao_id = request.data.get("organizacao_id")
        card_data = request.data.get("card")
        holder_info = request.data.get("holder")
        valor = request.data.get("valor")
        due_date = request.data.get("due_date")

        try:
            organizacao = Organizacao.objects.get(id=organizacao_id)
        except Organizacao.DoesNotExist:
            return Response({"error": "Organização não encontrada"}, status=404)

        if not organizacao.asaas_customer_id:
            return Response({"error": "A Organização não possui customer_id no ASAAS"}, status=400)

        provedor = ProvedorPagamento.objects.first()  # Ajuste conforme sua lógica para obter o provedor correto
        asaas = AsaasService(provedor)

        result = asaas.criar_assinatura_com_cartao(
            customer_id=organizacao.asaas_customer_id,
            valor=valor,
            due_date=due_date,
            card_data=card_data,
            holder_info=holder_info,
            external_id=f"organizacao_{organizacao.id}_assinatura"
        )

        # Se o ASAAS responder com erro
        if "errors" in result:
            return Response(result, status=400)

        # Se retornou o token, salvar
        token = result.get("creditCard", {}).get("creditCardToken")

        if token:
            organizacao.credit_card_token = token
            organizacao.save()

        return Response({
            "assinatura": result,
            "saved_token": token
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalhes_assinatura(request, assinatura_id=None):
    """API: Detalhes da assinatura (para React)"""
    try:
        if assinatura_id:
            assinatura = get_object_or_404(Assinatura, id=assinatura_id, organizacao=request.user.organizacao)
        else:
            try:
                assinatura = Assinatura.objects.get(organizacao=request.user.organizacao)
            except Assinatura.DoesNotExist:
                return Response({'assinatura': None, 'message': 'Nenhuma assinatura encontrada para esta organização'})

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

        return Response({
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
def cancelar_assinatura(request, assinatura_id):
    """API: Cancela uma assinatura (localmente)."""
    try:
        assinatura = get_object_or_404(Assinatura, id=assinatura_id, organizacao=request.user.organizacao)

        # Marcar cancelamento localmente
        assinatura.status = 'cancelada'
        assinatura.data_cancelamento = timezone.now()
        assinatura.save()

        # Opcional: cancelar transações pendentes
        assinatura.transacoes.filter(status='pending').update(status='cancelled')

        return Response({'success': True, 'message': 'Assinatura cancelada com sucesso'})
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# -------------------------
# Webhook (sem autenticação)
# -------------------------
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(['POST'])
def webhook_asaas(request):
    """Endpoint para webhooks (registro e tentativa de reconciliação local)."""
    try:
        payload = request.data  # usa request.data do DRF
        provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()

        # Registrar o webhook recebido
        evento = payload.get('event') or payload.get('type') or 'unknown'
        id_externo = None
        if isinstance(payload, dict):
            # tentar extrair um id externo razoável
            id_externo = payload.get('id') or payload.get('billingId') or payload.get('transactionId') or None

        WebhookLog.objects.create(
            provedor=provedor if provedor else (ProvedorPagamento.objects.first() if ProvedorPagamento.objects.exists() else None),
            payload=payload,
            evento=evento,
            id_externo=id_externo or '',
            processado=False
        )

        # Tentativa simples de processar eventos comuns:
        # - Se vier info de transação com id e status -> sincroniza TransacaoPagamento
        transacao_info = payload.get('transaction') or payload.get('payment') or payload.get('data') or payload
        if isinstance(transacao_info, dict):
            external_id = transacao_info.get('id') or transacao_info.get('transactionId') or transacao_info.get('chargeId')
            status_map = {
                'PAID': 'received',
                'CONFIRMED': 'confirmed',
                'PENDING': 'pending',
                'OVERDUE': 'overdue',
                'REFUNDED': 'refunded',
                'CANCELLED': 'cancelled'
            }
            ext_status = transacao_info.get('status', '').upper()
            mapped_status = status_map.get(ext_status, None)

            if external_id:
                tx = TransacaoPagamento.objects.filter(id_transacao_externo=external_id).first()
                if tx and mapped_status:
                    tx.status = mapped_status
                    if mapped_status in ('received', 'confirmed'):
                        tx.data_pagamento = timezone.now()
                    tx.dados_transacao.update({'webhook_payload': transacao_info})
                    tx.save()

                    # Se transação confirmada/recebida, ativa assinatura associada
                    assinatura = tx.assinatura
                    if mapped_status in ('received', 'confirmed') and assinatura and assinatura.status in ('trial', 'aguardando_pagamento'):
                        assinatura.status = 'ativa'
                        assinatura.data_proximo_pagamento = timezone.now() + timedelta(days=30)
                        assinatura.save()

        return Response({'status': 'success'})

    except Exception as e:
        return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
