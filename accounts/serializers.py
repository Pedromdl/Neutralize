from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DocumentoLegal, AceiteDocumento, Organizacao
from .services.profile_service import ProfilePictureService


User = get_user_model()

from .services.profile_service import ProfilePictureService

class OrganizacaoSerializer(serializers.ModelSerializer):
    total_usuarios = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()  # Novo campo
    
    class Meta:
        model = Organizacao
        fields = [
            'id', 'nome', 'tipo_pessoa', 'tipo', 'cnpj', 'cpf', 
            'logo', 'logo_url', 'endereco', 'numero', 'complemento', 
            'telefone', 'data_criacao', 'total_usuarios'
        ]
        read_only_fields = ['id', 'data_criacao', 'total_usuarios', 'logo_url']
    
    def get_total_usuarios(self, obj):
        return obj.UsuarioOrganizacao.count()
    
    def get_logo_url(self, obj):
        """Retorna URL da logo ou avatar padrão baseado no nome"""
        if obj.logo:
            # Se tem imagem, retorna URL completa
            if hasattr(obj.logo, 'url'):
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.logo.url)
                return obj.logo.url
            return str(obj.logo)
        
        # Fallback: gera avatar com iniciais
        return ProfilePictureService.generate_default_avatar_for_organization(obj)
    
    def validate(self, data):
        tipo_pessoa = data.get('tipo_pessoa', self.instance.tipo_pessoa if self.instance else 'pf')
        
        if tipo_pessoa == 'pj':
            if 'cnpj' in data and not data['cnpj']:
                raise serializers.ValidationError({"cnpj": "CNPJ é obrigatório para Pessoa Jurídica."})
        elif tipo_pessoa == 'pf':
            if 'cpf' in data and not data['cpf']:
                raise serializers.ValidationError({"cpf": "CPF é obrigatório para Pessoa Física."})
        
        return data

class OrganizacaoListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listagem
    """
    total_usuarios = serializers.SerializerMethodField()
    
    class Meta:
        model = Organizacao
        fields = [
            'id', 'nome', 'tipo_pessoa', 'tipo',
            'telefone', 'data_criacao', 'total_usuarios'
        ]
    
    def get_total_usuarios(self, obj):
        return obj.UsuarioOrganizacao.count()

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
