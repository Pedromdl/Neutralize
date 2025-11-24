# pagamentos/management/commands/debug_planos_asaas.py
from django.core.management.base import BaseCommand
from pagamentos.models import ProvedorPagamento
from pagamentos.services.asaas_client import AsaasClient
import requests
import json

class Command(BaseCommand):
    help = 'Debug detalhado da requisição de planos no ASAAS'
    
    def handle(self, *args, **options):
        try:
            provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()
            
            self.stdout.write('🔍 DEBUG DETALHADO - REQUISIÇÃO PLANOS ASAAS')
            self.stdout.write(f'📡 URL Base: {provedor.base_url}')
            self.stdout.write(f'🔑 API Key: {provedor.api_key[:20]}...')
            
            # Teste 1: Requisição direta com requests
            self.stdout.write('\n🧪 TESTE 1: Requisição direta com requests')
            url = f"{provedor.base_url}/plans"
            headers = {
                'accept': 'application/json',
                'access_token': provedor.api_key,
            }
            
            self.stdout.write(f'🌐 URL: {url}')
            self.stdout.write(f'📋 Headers: {headers}')
            
            response = requests.get(url, headers=headers, timeout=30)
            
            self.stdout.write(f'📊 Status Code: {response.status_code}')
            self.stdout.write(f'📄 Headers Resposta: {dict(response.headers)}')
            self.stdout.write(f'📝 Conteúdo (primeiros 500 chars): {response.text[:500]}')
            self.stdout.write(f'📏 Tamanho da resposta: {len(response.text)} bytes')
            
            # Teste 2: Tentar diferentes endpoints
            self.stdout.write('\n🧪 TESTE 2: Testando outros endpoints')
            
            endpoints = ['customers', 'subscriptions', 'payments']
            
            for endpoint in endpoints:
                self.stdout.write(f'\n🔍 Testando: /{endpoint}')
                test_url = f"{provedor.base_url}/{endpoint}"
                test_response = requests.get(test_url, headers=headers, timeout=30)
                self.stdout.write(f'   Status: {test_response.status_code}')
                self.stdout.write(f'   Tamanho: {len(test_response.text)} bytes')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Exception: {str(e)}'))