# pagamentos/views.py
from pytz import timezone as pytz_timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta, date, datetime
from django.shortcuts import get_object_or_404
from django.utils import timezone
import json
import uuid

from .models import ProvedorPagamento, PlanoPagamento, Assinatura, TransacaoPagamento, WebhookLog

# -------------------------
# Helpers locais / mocks
# -------------------------
def _generate_mock_card_token():
    """Gera um token mock para representar tokenização de cartão."""
    return f"mock_tok_{uuid.uuid4().hex[:24]}"

def _clean_number(value: str):
    if not value:
        return ""
    return ''.join(filter(str.isdigit, str(value)))

def _create_transacao_mock(assinatura: Assinatura, valor, metodo_pagamento='boleto', dias_vencimento=7):
    """Cria uma transação mock (boleto/PIX) vinculada à assinatura."""
    vencimento = date.today() + timedelta(days=dias_vencimento)
    transacao = TransacaoPagamento.objects.create(
        assinatura=assinatura,
        id_transacao_externo=f"local_{uuid.uuid4().hex[:12]}",
        valor=valor,
        data_vencimento=vencimento,
        status='pending',
        metodo_pagamento=metodo_pagamento,
        url_boleto=f"https://example.com/boleto/{uuid.uuid4().hex}" if metodo_pagamento == 'boleto' else None,
        codigo_pix=f"PIX-{uuid.uuid4().hex}" if metodo_pagamento == 'pix' else None,
        qrcode_pix=None if metodo_pagamento != 'pix' else f"qrcode:{uuid.uuid4().hex}",
        dados_transacao={"mock": True}
    )
    return transacao

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def criar_assinatura(request):
    """API: Cria assinatura para a CLÍNICA com suporte a cartão (local/mocked)."""
    try:
        user = request.user
        clinica = getattr(user, "clinica", None)
        if not clinica:
            return Response({'success': False, 'error': 'Usuário não associado a uma clínica.'}, status=status.HTTP_400_BAD_REQUEST)

        plano_id = request.data.get('plano_id')
        billing_type = (request.data.get('billing_type') or '').lower()  # expected: 'credit_card', 'boleto', 'pix'
        dados_cartao = request.data.get('dados_cartao')  # dict ou None

        # Verificar se já existe assinatura vinculada à clínica
        assinatura_existente = Assinatura.objects.filter(clinica=clinica).first()
        if assinatura_existente:
            return Response({
                'success': False,
                'error': 'Esta clínica já possui uma assinatura ativa/registrada.'
            }, status=status.HTTP_400_BAD_REQUEST)

        plano = get_object_or_404(PlanoPagamento, id=plano_id, ativo=True)

        # Decidir CPF/CNPJ (mesma lógica que você já tinha)
        cpf_cnpj = None
        customer_name = ""
        if getattr(clinica, 'cnpj', None):
            cpf_cnpj = _clean_number(clinica.cnpj)
            customer_name = clinica.nome
        elif getattr(user, 'cpf', None):
            cpf_cnpj = _clean_number(user.cpf)
            customer_name = user.get_full_name() or user.email
        else:
            return Response({'success': False, 'error': 'CNPJ da clínica ou CPF do administrador é obrigatório.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Criar assinatura local (em trial por padrão, com data_fim_trial conforme plano)
        assinatura = Assinatura.objects.create(
            clinica=clinica,
            plano=plano,
            provedor=ProvedorPagamento.objects.filter(ativo=True).first(),
            id_cliente_externo=None,
            id_assinatura_externo=None,
            data_fim_trial=timezone.now() + timedelta(days=plano.dias_trial) if plano.dias_trial else None,
            status='trial' if plano.dias_trial and plano.dias_trial > 0 else 'aguardando_pagamento',
            metodo_pagamento=billing_type if billing_type else None,
            metadata={
                'created_by_user': user.id,
                'customer_name': customer_name,
                'cpf_cnpj_used': cpf_cnpj
            }
        )

        # Fluxo quando pagamento for com cartão e dados do cartão foram enviados
        if billing_type == 'credit_card' and dados_cartao:
            # validações básicas
            credit = dados_cartao.get('creditCard', {})
            holder = dados_cartao.get('creditCardHolderInfo', {})

            required_fields = ['holderName', 'number', 'expiryMonth', 'expiryYear', 'ccv']
            for field in required_fields:
                if not credit.get(field):
                    assinatura.delete()
                    return Response({'success': False, 'error': f'Campo obrigatório do cartão não preenchido: {field}'},
                                    status=status.HTTP_400_BAD_REQUEST)

            required_holder_fields = ['name', 'email', 'cpfCnpj', 'postalCode', 'addressNumber', 'phone']
            for field in required_holder_fields:
                if not holder.get(field):
                    assinatura.delete()
                    return Response({'success': False, 'error': f'Campo obrigatório do titular não preenchido: {field}'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Tokenização mock (NUNCA salvar número completo)
            token = _generate_mock_card_token()
            ultimos = _clean_number(credit.get('number'))[-4:]
            bandeira = "UNKNOWN"
            if str(credit.get('number')).startswith('4'):
                bandeira = 'VISA'
            elif str(credit.get('number')).startswith('5'):
                bandeira = 'MASTERCARD'

            # Ativa assinatura localmente
            assinatura.ativar_com_cartao(cartao_token=token, ultimos_digitos=ultimos, bandeira=bandeira)

            return Response({
                'success': True,
                'assinatura': {
                    'id': assinatura.id,
                    'plano_nome': assinatura.plano.nome,
                    'status': assinatura.status,
                    'status_display': assinatura.get_status_display(),
                    'metodo_pagamento': assinatura.metodo_pagamento,
                    'data_proximo_pagamento': assinatura.data_proximo_pagamento.isoformat() if assinatura.data_proximo_pagamento else None,
                    'em_trial': assinatura.em_trial,
                    'data_fim_trial': assinatura.data_fim_trial.isoformat() if assinatura.data_fim_trial else None,
                    'id_assinatura_externo': assinatura.id_assinatura_externo
                }
            })

        else:
            # Fluxo boleto/PIX (criamos uma transação mock e marcamos aguardando pagamento)
            assinatura.status = 'aguardando_pagamento'
            assinatura.metodo_pagamento = billing_type
            assinatura.save()

            # Criar transação mock para o primeiro pagamento
            transacao = _create_transacao_mock(assinatura, valor=assinatura.plano.preco_mensal, metodo_pagamento=billing_type)

            return Response({
                'success': True,
                'assinatura': {
                    'id': assinatura.id,
                    'plano_nome': assinatura.plano.nome,
                    'status': assinatura.status,
                    'status_display': assinatura.get_status_display(),
                    'metodo_pagamento': assinatura.metodo_pagamento,
                    'data_proximo_pagamento': assinatura.data_proximo_pagamento.isoformat() if assinatura.data_proximo_pagamento else None,
                    'em_trial': assinatura.em_trial,
                    'data_fim_trial': assinatura.data_fim_trial.isoformat() if assinatura.data_fim_trial else None,
                    'id_assinatura_externo': assinatura.id_assinatura_externo
                },
                'transacao': {
                    'id': transacao.id_transacao_externo,
                    'valor': float(transacao.valor),
                    'data_vencimento': transacao.data_vencimento.isoformat(),
                    'url_boleto': transacao.url_boleto,
                    'codigo_pix': transacao.codigo_pix
                }
            })

    except Exception as e:
        # Em caso de erro, garantir que não deixamos assinatura meio-criada
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalhes_assinatura(request, assinatura_id=None):
    """API: Detalhes da assinatura (para React)"""
    try:
        if assinatura_id:
            assinatura = get_object_or_404(Assinatura, id=assinatura_id, clinica=request.user.clinica)
        else:
            try:
                assinatura = Assinatura.objects.get(clinica=request.user.clinica)
            except Assinatura.DoesNotExist:
                return Response({'assinatura': None, 'message': 'Nenhuma assinatura encontrada para esta clínica'})

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
        assinatura = get_object_or_404(Assinatura, id=assinatura_id, clinica=request.user.clinica)

        # Marcar cancelamento localmente
        assinatura.status = 'cancelada'
        assinatura.data_cancelamento = timezone.now()
        assinatura.save()

        # Opcional: cancelar transações pendentes
        assinatura.transacoes.filter(status='pending').update(status='cancelled')

        return Response({'success': True, 'message': 'Assinatura cancelada com sucesso'})
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cadastrar_cartao(request, assinatura_id):
    """Cadastra cartão após trial expirar (mock/local)."""
    try:
        assinatura = get_object_or_404(Assinatura, id=assinatura_id, clinica=request.user.clinica)

        # Verificar se está no status correto
        if assinatura.status != 'aguardando_pagamento':
            return Response({'success': False, 'error': 'Cartão só pode ser cadastrado após trial expirado'}, status=status.HTTP_400_BAD_REQUEST)

        # Dados do cartão do frontend
        dados_cartao = {
            'creditCard': {
                'holderName': request.data.get('nome_titular'),
                'number': request.data.get('numero_cartao'),
                'expiryMonth': request.data.get('mes_validade'),
                'expiryYear': request.data.get('ano_validade'),
                'ccv': request.data.get('cvv')
            },
            'creditCardHolderInfo': {
                'name': request.data.get('nome_titular'),
                'email': request.user.email,
                'cpfCnpj': getattr(request.user, 'cpf', '') or getattr(assinatura.clinica, 'cnpj', ''),
                'mobilePhone': getattr(request.user, 'phone', ''),
            }
        }

        credit = dados_cartao['creditCard']
        required_fields = ['holderName', 'number', 'expiryMonth', 'expiryYear', 'ccv']
        for field in required_fields:
            if not credit.get(field):
                return Response({'success': False, 'error': f'Campo obrigatório do cartão não preenchido: {field}'}, status=status.HTTP_400_BAD_REQUEST)

        # Tokenizar mock e ativar assinatura localmente
        token_response = {'creditCard': {'creditCardToken': _generate_mock_card_token(),
                                         'creditCardNumber': _clean_number(credit.get('number')),
                                         'creditCardBrand': 'VISA' if str(credit.get('number')).startswith('4') else 'MASTERCARD'}}

        if token_response and 'creditCard' in token_response:
            assinatura.cartao_token = token_response['creditCard']['creditCardToken']
            assinatura.ultimos_digitos = token_response['creditCard']['creditCardNumber'][-4:]
            assinatura.bandeira_cartao = token_response['creditCard']['creditCardBrand']

            # Ativar assinatura localmente
            assinatura.ativar_com_cartao(assinatura.cartao_token, assinatura.ultimos_digitos, assinatura.bandeira_cartao)

            return Response({'success': True, 'message': 'Cartão cadastrado com sucesso! Assinatura ativada.'})

        return Response({'success': False, 'error': 'Erro ao processar token do cartão'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ativar_assinatura_com_cartao(request, assinatura_id):
    """API: Ativa assinatura existente com cartão de crédito (mock/local)."""
    try:
        user = request.user
        assinatura = get_object_or_404(Assinatura, id=assinatura_id, clinica=user.clinica)
        dados_cartao = request.data.get('dados_cartao')

        # Validar se a assinatura pode ser ativada
        if assinatura.status != 'aguardando_pagamento':
            return Response({'success': False, 'error': 'Esta assinatura não pode ser ativada com cartão.'}, status=status.HTTP_400_BAD_REQUEST)

        # Preparar dados do cartão (mesma validação simples)
        credit = dados_cartao.get('creditCard', {})
        required_fields = ['holderName', 'number', 'expiryMonth', 'expiryYear', 'ccv']
        for field in required_fields:
            if not credit.get(field):
                return Response({'success': False, 'error': f'Campo obrigatório do cartão não preenchido: {field}'}, status=status.HTTP_400_BAD_REQUEST)

        # Tokenizar mock e ativar
        token = _generate_mock_card_token()
        ultimos = _clean_number(credit.get('number'))[-4:]
        bandeira = "VISA" if str(credit.get('number')).startswith('4') else "MASTERCARD"

        assinatura.ativar_com_cartao(cartao_token=token, ultimos_digitos=ultimos, bandeira=bandeira)

        return Response({
            'success': True,
            'assinatura': {
                'id': assinatura.id,
                'status': assinatura.status,
                'status_display': assinatura.get_status_display(),
                'metodo_pagamento': assinatura.metodo_pagamento,
                'data_proximo_pagamento': assinatura.data_proximo_pagamento.isoformat() if assinatura.data_proximo_pagamento else None,
            }
        })

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
