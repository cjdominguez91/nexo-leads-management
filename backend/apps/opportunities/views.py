from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.leads.services import leads_visibles_para

from .filters import OpportunityFilter
from .models import Opportunity
from .serializers import OpportunityPrioridadInputSerializer, OpportunitySerializer


class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """Nace siempre de tipificar un lead (ver apps.leads.services.tipificar_lead)
    — no hay creación manual. El alcance es el mismo que el del Lead que la
    origina: si puedes ver/gestionar el lead, puedes ver su oportunidad."""

    serializer_class = OpportunitySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OpportunityFilter
    ordering_fields = [
        "created_at",
        "fecha_proximo_contacto",
        "estado",
        "lead__documento_identidad",
        "lead__cliente_nombre",
        "campaign__nombre",
    ]

    def get_queryset(self):
        return Opportunity.objects.filter(lead__in=leads_visibles_para(self.request.user)).select_related(
            "lead__categoria_actual", "lead__subcategoria_actual", "campaign__campaign_type", "usuario_responsable"
        )

    @action(detail=True, methods=["post"], url_path="prioridad")
    def prioridad(self, request, pk=None):
        opportunity = self.get_object()
        serializer = OpportunityPrioridadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opportunity.prioridad = serializer.validated_data["prioridad"]
        opportunity.save(update_fields=["prioridad"])
        return Response(OpportunitySerializer(opportunity).data, status=status.HTTP_200_OK)
