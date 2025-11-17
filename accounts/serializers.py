from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DocumentoLegal, AceiteDocumento, Clinica

User = get_user_model()

class ClinicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinica
        fields = "__all__"

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'cpf', 'address', 'phone', 'birth_date')
        extra_kwargs = {'password': {'write_only': True}}

class CustomUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'cpf', 'address', 'phone', 'birth_date', 'role', 'is_staff')

class DocumentoLegalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoLegal
        fields = ['id', 'tipo', 'titulo', 'conteudo', 'versao', 'data_publicacao', 'ativo']


class AceiteDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AceiteDocumento
        fields = ['id', 'usuario', 'documento', 'data_aceite']
        read_only_fields = ['usuario', 'data_aceite']  # serão preenchidos automaticamente