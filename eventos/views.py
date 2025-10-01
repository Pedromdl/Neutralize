from django.shortcuts import render
from .models import EventoAgenda
from .serializers import EventoAgendaSerializer
from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets
import calendar



# Create your views here.
class EventoAgendaViewSet(viewsets.ModelViewSet):
    queryset = EventoAgenda.objects.all()
    serializer_class = EventoAgendaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['paciente']  # permite filtro por paciente

    def create(self, request, *args, **kwargs):
        dados = request.data
        repetir = dados.get("repetir", False)
        frequencia = dados.get("frequencia", "nenhuma")
        repeticoes = int(dados.get("repeticoes") or 0)

        # Evento principal
        serializer = self.get_serializer(data=dados)
        serializer.is_valid(raise_exception=True)
        evento_principal = serializer.save()

        eventos_criados = [evento_principal]

        # Eventos repetidos
        if repetir and frequencia != "nenhuma" and repeticoes > 0:
            data_base = evento_principal.data
            for i in range(1, repeticoes):
                nova_data = self.calcular_proxima_data(data_base, frequencia, i)
                novo_evento = EventoAgenda.objects.create(
                    paciente=evento_principal.paciente,
                    tipo=evento_principal.tipo,
                    status=evento_principal.status,
                    data=nova_data,
                    hora_inicio=evento_principal.hora_inicio,
                    hora_fim=evento_principal.hora_fim,
                    responsavel=evento_principal.responsavel,
                    repetir=False,
                    frequencia="nenhuma",
                    evento_pai=evento_principal
                )
                eventos_criados.append(novo_evento)

        return Response(
            EventoAgendaSerializer(eventos_criados, many=True).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # evento principal
        dados = request.data

        repetir = dados.get("repetir", False)
        frequencia = dados.get("frequencia", "nenhuma")
        repeticoes = int(dados.get("repeticoes") or 0)

        # Atualiza o evento principal
        serializer = self.get_serializer(instance, data=dados, partial=partial)
        serializer.is_valid(raise_exception=True)
        evento_atualizado = serializer.save()

        # Remove as ocorrências antigas vinculadas
        evento_atualizado.ocorrencias.all().delete()

        # Se precisa criar novas recorrências
        if repetir and frequencia != "nenhuma" and repeticoes > 0:
            data_base = evento_atualizado.data
            for i in range(1, repeticoes):
                nova_data = self.calcular_proxima_data(data_base, frequencia, i)
                EventoAgenda.objects.create(
                    paciente=evento_atualizado.paciente,
                    tipo=evento_atualizado.tipo,
                    status=evento_atualizado.status,
                    data=nova_data,
                    hora_inicio=evento_atualizado.hora_inicio,
                    hora_fim=evento_atualizado.hora_fim,
                    responsavel=evento_atualizado.responsavel,
                    repetir=False,
                    frequencia="nenhuma",
                    evento_pai=evento_atualizado
                )

        return Response(self.get_serializer(evento_atualizado).data, status=status.HTTP_200_OK)

    def calcular_proxima_data(self, data_inicial, frequencia, i):
        if frequencia == "diario":
            return data_inicial + timedelta(days=i)
        elif frequencia == "semanal":
            return data_inicial + timedelta(weeks=i)
        elif frequencia == "mensal":
            # Ajuste simples para meses futuros
            mes = data_inicial.month - 1 + i
            ano = data_inicial.year + mes // 12
            mes = mes % 12 + 1
            dia = min(data_inicial.day, calendar.monthrange(ano, mes)[1])
            return data_inicial.replace(year=ano, month=mes, day=dia)
        return data_inicial