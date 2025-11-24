# pagamentos/management/commands/listar_planos_asaas.py
from django.core.management.base import BaseCommand
from pagamentos.models import ProvedorPagamento
from pagamentos.services.asaas_client import AsaasClient

class Command(BaseCommand):
    help = 'Listar planos existentes no ASAAS'
    
    def handle(self, *args, **options):
        try:
            provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()
            client = AsaasClient(provedor)
            
            self.stdout.write('📋 Buscando planos existentes no ASAAS...')
            response = client._make_request('GET', 'plans')
            
            if response and 'data' in response:
                planos = response['data']
                self.stdout.write(self.style.SUCCESS(f'✅ Encontrados {len(planos)} planos:'))
                
                for plano in planos:
                    self.stdout.write(f"""
┌─ Plano ASAAS ──────────────────────
│ ID: {plano.get('id')}
│ Nome: {plano.get('name')} 
│ Valor: R$ {plano.get('value')}
│ Status: {plano.get('status')}
│ Ciclo: {plano.get('cycle')}
└────────────────────────────────────
                    """)
                    
                    # Se já existir um plano Starter, use esse ID
                    if 'starter' in plano.get('name', '').lower():
                        self.stdout.write(self.style.SUCCESS(f'🎯 Plano Starter encontrado! Use este ID: {plano["id"]}'))
                        
            else:
                self.stdout.write('📝 Nenhum plano encontrado no ASAAS')
                if response:
                    self.stdout.write(f'Resposta: {response}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro: {str(e)}'))