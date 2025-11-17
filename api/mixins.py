import logging
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

class ClinicFilterMixin:
    """
    Filtra qualquer queryset pelo campo 'clinica'
    e automaticamente atribui a clínica do usuário logado ao criar novos registros.
    """
    clinica_field = "clinica"  # Nome do campo no modelo que representa a clínica

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not hasattr(user, "clinica") or user.clinica is None:
            logger.warning(f"Usuário {user} não possui clínica associada. Retornando queryset vazio.")
            return qs.none()

        logger.info(f"Filtrando {self.__class__.__name__} pela clínica {user.clinica}")
        return qs.filter(**{self.clinica_field: user.clinica})

    def perform_create(self, serializer):
        """
        Garante que todo novo registro criado automaticamente receba
        a mesma 'clinica' do usuário logado.
        """
        user = self.request.user

        if not hasattr(user, "clinica") or user.clinica is None:
            logger.error(f"Usuário {user} tentou criar registro sem clínica associada.")
            raise PermissionDenied("Usuário não possui clínica associada.")

        logger.info(f"Criando {serializer.Meta.model.__name__} com clínica {user.clinica} para usuário {user}")
        serializer.save(**{self.clinica_field: user.clinica})
