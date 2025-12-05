# services/profile_service.py
import hashlib
from typing import Optional
from accounts.models import CustomUser

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
        # Pega iniciais
        initials = ProfilePictureService._get_user_initials(user)
        
        # Serviços de avatar baseados em inicial
        services = [
            lambda: f"https://ui-avatars.com/api/?name={initials}&background=random&color=fff&size={size}",
            lambda: f"https://avatar.oxro.io/avatar.svg?name={initials}&background=random",
            lambda: ProfilePictureService._get_gravatar_url(user.email, size) if user.email else None
        ]
        
        # Tenta o primeiro serviço disponível
        for service in services:
            try:
                url = service()
                if url:
                    return url
            except:
                continue
        
        # Fallback final
        return f"https://ui-avatars.com/api/?name={initials}&size={size}"
    
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
    def _get_gravatar_url(email: str, size: int) -> str:
        """Gera URL do Gravatar"""
        email_hash = hashlib.md5(email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s={size}"