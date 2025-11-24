# accounts/management/commands/criar_planos.py
from django.core.management.base import BaseCommand
from accounts.models import Plano

class Command(BaseCommand):
    def handle(self, *args, **options):
        planos = [
            {
                'nome': 'Starter',
                'tipo': 'starter',
                'preco_mensal': 97.00,
                'max_pacientes': 15,
                'max_usuarios': 1,
                'max_avaliacoes_mes': 50,
                'dias_trial': 30,
                'recursos': {
                    'avaliacoes_basicas': True,
                    'relatorios_pdf': True,
                    'app_paciente': True,
                    'suporte_email': True
                }
            },
            {
                'nome': 'Professional', 
                'tipo': 'professional',
                'preco_mensal': 297.00,
                'max_pacientes': 50,
                'max_usuarios': 3,
                'max_avaliacoes_mes': 200,
                'dias_trial': 14,
                'recursos': {
                    'avaliacoes_basicas': True,
                    'avaliacoes_avancadas': True,
                    'relatorios_pdf': True,
                    'relatorios_personalizaveis': True,
                    'app_paciente': True,
                    'multi_usuario': True,
                    'branding': True,
                    'suporte_prioritario': True
                }
            },
            {
                'nome': 'Clinic',
                'tipo': 'clinic', 
                'preco_mensal': 597.00,
                'max_pacientes': 0,  # 0 = ilimitado
                'max_usuarios': 0,   # 0 = ilimitado  
                'max_avaliacoes_mes': 0,  # 0 = ilimitado
                'dias_trial': 7,
                'recursos': {
                    'todos_recursos': True,
                    'api_integracao': True,
                    'white_label': True,
                    'suporte_dedicado': True,
                    'customizacoes': True
                }
            }
        ]
        
        for plano_data in planos:
            plano, created = Plano.objects.update_or_create(
                tipo=plano_data['tipo'],
                defaults=plano_data
            )
            if created:
                self.stdout.write(f"Plano {plano.nome} criado")
            else:
                self.stdout.write(f"Plano {plano.nome} atualizado")