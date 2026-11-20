from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from apps.core.mixins import DivisionScopedViewSetMixin

from .models import Agencia, Territorio
from .serializers import AgenciaSerializer, TerritorioSerializer


class TerritorioViewSet(DivisionScopedViewSetMixin, viewsets.ModelViewSet):
    """Lectura: cualquier autenticado, solo distritos de su división (lo
    necesitan filtros, restricciones de campaña/lote, etc.). Escritura:
    ADMIN (cualquier división) o ADMIN_DIVISION (la suya)."""

    queryset = Territorio.objects.select_related("division").all()
    serializer_class = TerritorioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "division"]
    division_lookup = "division"


class AgenciaViewSet(DivisionScopedViewSetMixin, viewsets.ModelViewSet):
    """Igual que TerritorioViewSet. La división de una agencia es la de su
    distrito (no tiene FK propia)."""

    queryset = Agencia.objects.select_related("territorio__division").all()
    serializer_class = AgenciaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {"activo": ["exact"], "territorio": ["exact"], "territorio__division": ["exact"]}
    division_lookup = "territorio__division"
