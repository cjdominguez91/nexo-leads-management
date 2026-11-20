from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.core.permissions import IsAdminOrGerente

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de trazabilidad general. Solo ADMIN/GERENTE (lectura global).

    La "cadena de custodia" por lead específico (historial de Assignment)
    se expone en apps.leads en la Fase 2 — este endpoint es la vista
    genérica de auditoría de todo el sistema, no la vista contextual del lead."""

    queryset = AuditLog.objects.select_related("usuario").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminOrGerente]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["usuario", "accion", "modelo_afectado"]
