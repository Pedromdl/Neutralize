from rest_framework import viewsets
from .models import LancamentoFinanceiro
from .serializers import LancamentoFinanceiroSerializer

class LancamentoFinanceiroViewSet(viewsets.ModelViewSet):
    queryset = LancamentoFinanceiro.objects.all().select_related("paciente", "evento")
    serializer_class = LancamentoFinanceiroSerializer

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True  # 🔹 permite atualizar só alguns campos
        return super().update(request, *args, **kwargs)