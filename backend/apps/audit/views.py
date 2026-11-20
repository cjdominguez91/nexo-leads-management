from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.core.permissions import IsAdminOrGerente
from apps.core.scoping import filtrar_por_division

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de trazabilidad general. ADMIN: todo. ADMIN_DIVISION/GERENTE:
    solo acciones hechas por usuarios de su división.

    Limitación conocida: las acciones de un ADMIN global sobre objetos de una
    división no aparecen para el ADMIN_DIVISION/GERENTE de esa división (el
    AuditLog guarda quién actuó, no la división del objeto afectado).

    La "cadena de custodia" por lead específico (historial de Assignment)
    se expone en apps.leads — este endpoint es la vista genérica de
    auditoría del sistema, no la vista contextual del lead."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminOrGerente]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["usuario", "accion", "modelo_afectado"]

    def get_queryset(self):
        qs = AuditLog.objects.select_related("usuario")
        return filtrar_por_division(qs, self.request.user, "usuario__division")
