import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from eventos.models import EventoAgenda
from accounts.models import Clinica

clinica2 = Clinica.objects.get(id=2)

updated = EventoAgenda.objects.filter(clinica__isnull=True).update(clinica=clinica2)

print(f"{updated} eventos atribuídos à clínica 2")
