from rest_framework.permissions import BasePermission

class IsProfissional(BasePermission):
    """
    Permite acesso apenas a usuários com role 'profissional'.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'profissional'


class IsPaciente(BasePermission):
    """
    Permite acesso apenas a usuários com role 'paciente'.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'paciente'
