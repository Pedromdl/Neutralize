
from rest_framework import serializers
from .models import EventoAgenda

class EventoAgendaSerializer(serializers.ModelSerializer):
    paciente_nome = serializers.CharField(source='paciente.nome', read_only=True)  # nome do paciente vindo do related

    class Meta:
        model = EventoAgenda
        fields = '__all__'