# pagamentos/management/commands/1_criar_plano_asaas.py
from django.core.management.base import BaseCommand
from pagamentos.models import ProvedorPagamento
from pagamentos.services.asaas_client import AsaasClient

class Command(BaseCommand):
    help = 'PASSO 1: Criar plano no ASAAS'
    
    def handle(self, *args, **options):
        try:
            provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()
            if not provedor:
                self.stdout.write(self.style.ERROR('❌ Configure o ProvedorPagamento no admin primeiro!'))
                return
            
            client = AsaasClient(provedor)
            
            data = {
                "name": "Plano Starter",
                "value": 99.00,
                "billingType": "RECURRING", 
                "cycle": "MONTHLY",
                "description": "Plano para profissionais autônomos",
            }
            
            response = client._make_request('POST', 'plans', data)
            
            if response and 'id' in response:
                self.stdout.write(self.style.SUCCESS('✅ PASSO 1 CONCLUÍDO: Plano criado no ASAAS!'))
                self.stdout.write(f"""
⚠️ ⚠️ ⚠️  ANOTE ESTE ID ⚠️ ⚠️ ⚠️ 
ID DO PLANO: {response['id']}

👉 AGORA VÁ NO ADMIN DJANGO E:
1. Acesse PlanoPagamento
2. Crie um plano com:
   - Nome: "Starter" 
   - ID Externo: "{response['id']}"
   - Preço: 99.00
   - Outros campos conforme necessário
                """)
            else:
                self.stdout.write(self.style.ERROR('❌ Erro ao criar plano'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Exception: {str(e)}'))