# pagamentos/management/commands/testar_conexao_asaas.py
from django.core.management.base import BaseCommand
from pagamentos.models import ProvedorPagamento
from pagamentos.services.asaas_client import AsaasClient
import requests

class Command(BaseCommand):
    help = 'Testar conexão básica com ASAAS'
    
    def handle(self, *args, **options):
        try:
            provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()
            
            if not provedor:
                self.stdout.write(self.style.ERROR('❌ ProvedorPagamento não encontrado. Configure no admin primeiro!'))
                return
            
            self.stdout.write(f'🔍 Testando conexão com: {provedor.nome}')
            self.stdout.write(f'📡 URL Base: {provedor.base_url}')
            self.stdout.write(f'🔑 API Key: {provedor.api_key[:10]}...' if provedor.api_key else '❌ API Key vazia!')
            
            # Teste direto com requests
            url = f"{provedor.base_url}/customers"
            headers = {
                'accept': 'application/json',
                'access_token': provedor.api_key,
                'content-type': 'application/json'
            }
            
            self.stdout.write(f'🌐 Fazendo requisição para: {url}')
            
            response = requests.get(url, headers=headers)
            
            self.stdout.write(f'📊 Status Code: {response.status_code}')
            self.stdout.write(f'📄 Conteúdo da resposta: {response.text[:200]}...')
            
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS('✅ Conexão com ASAAS funcionando!'))
            elif response.status_code == 401:
                self.stdout.write(self.style.ERROR('❌ Erro 401 - API Key inválida ou não configurada'))
            elif response.status_code == 404:
                self.stdout.write(self.style.ERROR('❌ Erro 404 - URL incorreta'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Erro HTTP: {response.status_code}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Exception: {str(e)}'))