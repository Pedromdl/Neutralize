from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.utils import timezone
from integracoes.services.google_contacts import GoogleContactsService
from .models import Contact, AcaoPlanejada
import re

def normalize_phone(phone):
    if not phone:
        return None
    return re.sub(r"\D", "", phone)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_google_contacts(request):
    user = request.user

    service = GoogleContactsService(user)
    response = service.fetch_contacts()

    connections = response.get("connections", [])

    created = 0
    skipped = 0

    # 🔍 Telefones já existentes no banco
    existing_phones = set(
        Contact.objects
        .filter(user=user)
        .exclude(phone__isnull=True)
        .values_list("phone", flat=True)
    )

    for person in connections:
        name = (
            person.get("names", [{}])[0]
            .get("displayName", "Sem nome")
        )

        raw_phone = (
            person.get("phoneNumbers", [{}])[0]
            .get("value")
        )

        phone = normalize_phone(raw_phone)

        if not phone:
            skipped += 1
            continue

        if phone in existing_phones:
            skipped += 1
            continue

        email = (
            person.get("emailAddresses", [{}])[0]
            .get("value")
        )

        Contact.objects.create(
            user=user,
            name=name,
            phone=phone,
            email=email,
            source="google"
        )

        existing_phones.add(phone)
        created += 1

    return JsonResponse({
        "imported": created,
        "skipped": skipped,
        "total_google": len(connections),
        "total_db": Contact.objects.filter(user=user).count()
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_contacts(request):
    user = request.user

    contacts = (
        Contact.objects
        .filter(user=user)
        .order_by("name")
        .values("id", "name", "phone", "email")
    )

    return JsonResponse(list(contacts), safe=False)

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from crm.models import Contact, Interacao
from crm.serializers import ContactStatusSerializer, ContactSerializer, InteracaoSerializer, AcaoPlanejadaSerializer
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend


class ContactViewSet(ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer  # o geral
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["arquivado"]


    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        contact = self.get_object()
        serializer = ContactStatusSerializer(
            contact,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class InteracaoViewSet(ReadOnlyModelViewSet):
    serializer_class = InteracaoSerializer

    def get_queryset(self):
        pessoa_id = self.kwargs.get("pessoa_id")
        return Interacao.objects.filter(pessoa_id=pessoa_id)
    
class AcaoPlanejadaViewSet(ModelViewSet):
    serializer_class = AcaoPlanejadaSerializer

    def get_queryset(self):
        user = self.request.user

        queryset = AcaoPlanejada.objects.filter(
            pessoa__user=user,
            concluida=False
        )

        pessoa_id = self.request.query_params.get("pessoa")
        if pessoa_id:
            queryset = queryset.filter(pessoa_id=pessoa_id)

        return queryset.order_by("data_planejada")

    @action(detail=True, methods=["patch"])
    def concluir(self, request, pk=None):
        acao = self.get_object()

        if acao.concluida:
            return Response(
                {"detail": "Ação já foi concluída."},
                status=status.HTTP_400_BAD_REQUEST
            )

        descricao_interacao = request.data.get("descricao", "").strip()

        if not descricao_interacao:
            return Response(
                {"detail": "Descrição da interação é obrigatória."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1️⃣ Conclui a ação
        acao.concluida = True
        acao.data_execucao = timezone.now()
        acao.save()

        # 2️⃣ Cria interação
        interacao = Interacao.objects.create(
            pessoa=acao.pessoa,
            tipo=acao.tipo,
            descricao=descricao_interacao,
            data=acao.data_execucao,
        )

        # 3️⃣ 🔥 ATUALIZA DATA DO ÚLTIMO CONTATO
        contato = acao.pessoa
        contato.data_ultimo_contato = interacao.data
        contato.save(update_fields=["data_ultimo_contato"])

        return Response(
            {
                "acao": AcaoPlanejadaSerializer(acao).data,
                "interacao": InteracaoSerializer(interacao).data,
            },
            status=status.HTTP_200_OK
        )