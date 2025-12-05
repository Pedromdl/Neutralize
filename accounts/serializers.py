from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DocumentoLegal, AceiteDocumento
from .services.profile_service import ProfilePictureService


User = get_user_model()

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'cpf', 'address', 'phone', 'birth_date')
        extra_kwargs = {'password': {'write_only': True}}

class CustomUserSerializer(UserSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = ('id', 'email', 'photo_google', 'profile_picture_url', 'first_name', 'last_name', 'cpf', 'address', 'phone', 'birth_date', 'role', 'is_staff')
            
    def get_profile_picture_url(self, obj):
        """Retorna a foto do Google ou a padrão"""
        return ProfilePictureService.get_profile_picture_url(obj)

class DocumentoLegalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoLegal
        fields = ['id', 'tipo', 'titulo', 'conteudo', 'versao', 'data_publicacao', 'ativo']


class AceiteDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AceiteDocumento
        fields = ['id', 'usuario', 'documento', 'data_aceite']
        read_only_fields = ['usuario', 'data_aceite']  # serão preenchidos automaticamente
