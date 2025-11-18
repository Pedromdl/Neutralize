import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from api.models import (
    Mobilidade,
    ForcaMuscular,
    Estabilidade,
    TesteFuncao,
    TesteDor,
    Usuário
)

print("🔍 Selecionando pacientes da clínica 3...")
pacientes = Usuário.objects.filter(clinica_id=3)

# Apagar dados
Mobilidade.objects.filter(paciente__in=pacientes).delete()
ForcaMuscular.objects.filter(paciente__in=pacientes).delete()
Estabilidade.objects.filter(paciente__in=pacientes).delete()
TesteFuncao.objects.filter(paciente__in=pacientes).delete()
TesteDor.objects.filter(paciente__in=pacientes).delete()

print("✅ Todos os dados de avaliações da clínica 3 foram apagados!")
