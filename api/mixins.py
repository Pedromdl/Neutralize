import logging
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

class OrganizacaoFilterMixin:
    """
    Filtra qualquer queryset pelo campo 'organizacao'
    e automaticamente atribui a organização do usuário logado ao criar novos registros.
    """
    organizacao_field = "organizacao"  # Nome do campo no modelo

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not hasattr(user, "organizacao") or user.organizacao is None:
            logger.warning(f"Usuário {user} não possui organização associada.")
            return qs.none()

        logger.info(f"Filtrando {self.__class__.__name__} pela organização {user.organizacao}")
        return qs.filter(**{self.organizacao_field: user.organizacao})

    def perform_create(self, serializer):
        user = self.request.user

        if not hasattr(user, "organizacao") or user.organizacao is None:
            logger.error(f"Usuário {user} tentou criar registro sem organização associada.")
            raise PermissionDenied("Usuário não possui organização associada.")

        logger.info(
            f"Criando {serializer.Meta.model.__name__} com organização {user.organizacao} para o usuário {user}"
        )

        serializer.save(**{self.organizacao_field: user.organizacao})