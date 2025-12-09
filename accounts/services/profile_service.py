# services/profile_service.py
import hashlib
from typing import Optional
from accounts.models import CustomUser, Organizacao  # Adicione o import

class ProfilePictureService:
    
    @staticmethod
    def get_profile_picture_url(user: 'CustomUser', size: int = 128) -> str:
        """Retorna URL da foto de perfil com fallback"""
        if user.photo_google:
            return user.photo_google
        
        return ProfilePictureService.generate_default_avatar(user, size)
    
    @staticmethod
    def generate_default_avatar(user: 'CustomUser', size: int = 128) -> str:
        """Gera URL de avatar padrão baseado no usuário"""
        initials = ProfilePictureService._get_user_initials(user)
        
        # Serviços de avatar
        services = [
            lambda: f"https://ui-avatars.com/api/?name={initials}&background=random&color=fff&size={size}",
            lambda: f"https://avatar.oxro.io/avatar.svg?name={initials}&background=random",
            lambda: ProfilePictureService._get_gravatar_url(user.email, size) if user.email else None
        ]
        
        for service in services:
            try:
                url = service()
                if url:
                    return url
            except:
                continue
        
        return f"https://ui-avatars.com/api/?name={initials}&size={size}"
    
    @staticmethod
    def generate_default_avatar_for_organization(org: 'Organizacao', size: int = 128) -> str:
        """Gera URL de avatar padrão baseado na organização"""
        initials = ProfilePictureService._get_organization_initials(org)
        
        # Cores específicas para tipos de organização
        color_map = {
            'clinica': '3498db',     # Azul
            'consultorio': '2ecc71', # Verde
            'estudio': '9b59b6',     # Roxo
            'autonomo': 'e74c3c',    # Vermelho
            'online': '1abc9c',      # Turquesa
            'instituto': 'f39c12',   # Laranja
            'outro': '95a5a6',       # Cinza
        }
        
        background = color_map.get(org.tipo, 'random')
        
        return f"https://ui-avatars.com/api/?name={initials}&background={background}&color=fff&size={size}"
    
    @staticmethod
    def _get_user_initials(user: 'CustomUser') -> str:
        """Extrai iniciais do usuário"""
        if user.first_name and user.last_name:
            return f"{user.first_name[0]}{user.last_name[0]}".upper()
        elif user.first_name:
            return user.first_name[0].upper()
        elif user.last_name:
            return user.last_name[0].upper()
        elif user.email:
            return user.email[0].upper()
        return "U"
    
    @staticmethod
    def _get_organization_initials(org: 'Organizacao') -> str:
        """Extrai iniciais da organização"""
        if org.nome:
            # Pega as iniciais das palavras principais
            words = org.nome.split()
            if len(words) >= 2:
                return f"{words[0][0]}{words[1][0]}".upper()
            return org.nome[:2].upper()
        # Fallback baseado no tipo
        tipo_map = {
            'clinica': 'CL',
            'consultorio': 'CO',
            'estudio': 'ES',
            'autonomo': 'PA',
            'online': 'SO',
            'instituto': 'EI',
            'outro': 'OR',
        }
        return tipo_map.get(org.tipo, 'OR')
    
    @staticmethod
    def _get_gravatar_url(email: str, size: int) -> str:
        """Gera URL do Gravatar"""
        email_hash = hashlib.md5(email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s={size}"