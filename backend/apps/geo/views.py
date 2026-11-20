from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsAdmin

from .models import Agencia, Territorio
from .serializers import AgenciaSerializer, TerritorioSerializer


class _CatalogViewSet(viewsets.ModelViewSet):
    """Lectura: cualquier usuario autenticado — cualquier pantalla que
    necesite elegir/mostrar una agencia o distrito (restricción de campaña,
    restricción de lote, filtros) necesita poder leer este catálogo, no
    solo ADMIN. Escritura (alta/baja/edición): solo ADMIN."""

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


class TerritorioViewSet(_CatalogViewSet):
    queryset = Territorio.objects.all()
    serializer_class = TerritorioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo"]


class AgenciaViewSet(_CatalogViewSet):
    queryset = Agencia.objects.select_related("territorio").all()
    serializer_class = AgenciaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo", "territorio"]
