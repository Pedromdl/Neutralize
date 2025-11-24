# pagamentos/management/commands/testar_assinatura_real.py
from django.core.management.base import BaseCommand
from pagamentos.models import ProvedorPagamento, PlanoPagamento
from accounts.models import Clinica
from backend.pagamentos.services.assinatura_service import AssinaturaService

class Command(BaseCommand):
    help = 'Testar criação REAL de assinatura no ASAAS'
    
    def handle(self, *args, **options):
        try:
            provedor = ProvedorPagamento.objects.filter(ativo=True, tipo='asaas').first()
            plano = PlanoPagamento.objects.filter(ativo=True).first()
            clinica = Clinica.objects.first()
            
            if not all([provedor, plano, clinica]):
                self.stdout.write(self.style.ERROR('❌ Dados incompletos'))
                return
            
            self.stdout.write(f'🏥 Clínica: {clinica.nome}')
            self.stdout.write(f'📋 Plano: {plano.nome} - R$ {plano.preco_mensal}')
            
            service = AssinaturaService(provedor)
            
            # Testar com PIX (mais simples)
            assinatura = service.criar_assinatura(
                clinica=clinica,
                plano=plano,
                billing_type='PIX',
                customer_data={
                    'email': 'teste@clinica.com',
                    'name': clinica.nome
                }
            )
            
            self.stdout.write(self.style.SUCCESS('✅ ASSINATURA CRIADA COM SUCESSO!'))
            self.stdout.write(f'📝 ID Local: {assinatura.id}')
            self.stdout.write(f'👤 ID Cliente ASAAS: {assinatura.id_cliente_externo}')
            self.stdout.write(f'🔄 ID Assinatura ASAAS: {assinatura.id_assinatura_externo}')
            self.stdout.write(f'📊 Status: {assinatura.status}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro: {str(e)}'))