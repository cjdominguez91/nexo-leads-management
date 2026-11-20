from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.accounts.constants import GLOBAL_SCOPE_ROLES
from apps.core.permissions import IsAdmin
from apps.core.scoping import campanas_visibles_para
from apps.leads.tasks import procesar_lote_carga

from rest_framework.exceptions import ValidationError

from .models import Campaign, CampaignFieldDefinition, CampaignSection, CampaignType, LoteCarga
from .serializers import (
    CampaignFieldDefinitionSerializer,
    CampaignSectionSerializer,
    CampaignSerializer,
    CampaignTypeSerializer,
    LoteCargaSerializer,
)


class CampaignTypeViewSet(viewsets.ModelViewSet):
    """Lectura: cualquier usuario autenticado — el esquema de campos es lo
    que le permite al frontend renderizar la tabla/detalle dinámico de
    leads, así que quien puede ver leads necesita poder leer esto.
    Escritura: solo ADMIN (es quien define el esquema de cada producto)."""

    queryset = CampaignType.objects.prefetch_related("field_definitions")
    serializer_class = CampaignTypeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["categoria", "modo_carga"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


class CampaignFieldDefinitionViewSet(viewsets.ModelViewSet):
    """Mismo criterio que CampaignTypeViewSet: lectura abierta, escritura ADMIN."""

    queryset = CampaignFieldDefinition.objects.all()
    serializer_class = CampaignFieldDefinitionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campaign_type", "origen"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


class CampaignSectionViewSet(viewsets.ModelViewSet):
    """Lectura abierta (el frontend arma el formulario/tabla dinámicos con
    esto), escritura ADMIN. "Datos del cliente" (es_obligatoria=True) no se
    puede eliminar ni tiene sentido que quede sin campos aunque no esté
    protegida a nivel de base — se valida acá."""

    queryset = CampaignSection.objects.all()
    serializer_class = CampaignSectionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campaign_type"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_destroy(self, instance):
        if instance.es_obligatoria:
            raise ValidationError("Esta sección es del sistema y no se puede eliminar.")
        if instance.campos.exists():
            raise ValidationError("Mueve o elimina los campos de esta sección antes de eliminarla.")
        instance.delete()


def _role(user):
    return getattr(user.role, "nombre", None) if getattr(user, "role_id", None) else None


class CampaignViewSet(viewsets.ModelViewSet):
    """Lectura: cualquier usuario autenticado, filtrado por su división
    (salvo ADMIN/GERENTE, que ven todas). Escritura: solo ADMIN."""

    serializer_class = CampaignSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "estado": ["exact"],
        "campaign_type": ["exact"],
        "division": ["exact"],
        "campaign_type__modo_carga": ["exact"],
    }
    search_fields = ["nombre", "producto_default"]
    ordering_fields = ["nombre", "fecha_inicio", "fecha_fin", "estado", "created_at"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Campaign.objects.select_related("campaign_type", "division")
        return qs.filter(pk__in=campanas_visibles_para(self.request.user).values_list("pk", flat=True))


class LoteCargaViewSet(viewsets.ModelViewSet):
    """Lectura: cualquier usuario autenticado (dentro de su scope de
    queryset) — quien gestiona un lead debe poder ver de qué archivo vino,
    aunque no lo haya subido él. Escritura (subir archivo): solo ADMIN."""

    serializer_class = LoteCargaSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campaign", "estado"]
    http_method_names = ["get", "post", "head", "options"]  # append-only: sin edición/borrado

    def get_permissions(self):
        if self.action == "create":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = LoteCarga.objects.select_related("campaign", "usuario_carga")
        user = self.request.user
        if user.is_superuser or _role(user) in GLOBAL_SCOPE_ROLES:
            return qs
        return qs.filter(Q(usuario_carga=user) | Q(campaign__in=campanas_visibles_para(user)))

    def perform_create(self, serializer):
        lote = serializer.save()
        procesar_lote_carga.delay(lote.id)
