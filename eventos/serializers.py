
from rest_framework import serializers
from .models import EventoAgenda

class EventoAgendaSerializer(serializers.ModelSerializer):
    paciente_nome = serializers.CharField(source='paciente.nome', read_only=True)

    class Meta:
        model = EventoAgenda
        fields = '__all__'
        read_only_fields = ['id']  # garante que o id não seja enviado no update