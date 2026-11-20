from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from apps.core.mixins import WRITE_ACTIONS, DivisionScopedViewSetMixin
from apps.core.permissions import IsAdminRole
from apps.core.scoping import campanas_visibles_para, es_global
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


class CampaignTypeViewSet(DivisionScopedViewSetMixin, viewsets.ModelViewSet):
    """Lectura: cualquier autenticado, solo tipos de su división — el
    esquema de campos es lo que le permite al frontend renderizar la tabla/
    detalle dinámico de leads. Escritura: ADMIN o ADMIN_DIVISION (la suya)."""

    queryset = CampaignType.objects.select_related("division").prefetch_related("field_definitions")
    serializer_class = CampaignTypeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["categoria", "modo_carga", "division"]
    division_lookup = "division"


class CampaignFieldDefinitionViewSet(DivisionScopedViewSetMixin, viewsets.ModelViewSet):
    """Mismo criterio que CampaignTypeViewSet; la división es la de su tipo."""

    queryset = CampaignFieldDefinition.objects.all()
    serializer_class = CampaignFieldDefinitionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campaign_type", "origen"]
    division_lookup = "campaign_type__division"


class CampaignSectionViewSet(DivisionScopedViewSetMixin, viewsets.ModelViewSet):
    """Lectura (el frontend arma el formulario/tabla dinámicos con esto) y
    escritura con el mismo criterio que CampaignTypeViewSet. "Datos del
    cliente" (es_obligatoria=True) no se puede eliminar ni tiene sentido que
    quede sin campos aunque no esté protegida a nivel de base — se valida acá."""

    queryset = CampaignSection.objects.all()
    serializer_class = CampaignSectionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campaign_type"]
    division_lookup = "campaign_type__division"

    def perform_destroy(self, instance):
        if instance.es_obligatoria:
            raise ValidationError("Esta sección es del sistema y no se puede eliminar.")
        if instance.campos.exists():
            raise ValidationError("Mueve o elimina los campos de esta sección antes de eliminarla.")
        instance.delete()


class CampaignViewSet(viewsets.ModelViewSet):
    """Lectura: cualquier autenticado, según campanas_visibles_para (su
    división + su alcance territorial). Escritura: ADMIN o ADMIN_DIVISION;
    como el queryset ya está filtrado, un ADMIN_DIVISION solo edita campañas
    de su división."""

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
        if self.action in WRITE_ACTIONS:
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Campaign.objects.select_related("campaign_type", "division")
        return qs.filter(pk__in=campanas_visibles_para(self.request.user).values_list("pk", flat=True))


class LoteCargaViewSet(viewsets.ModelViewSet):
    """Lectura: cualquier usuario autenticado (dentro de su scope de
    queryset) — quien gestiona un lead debe poder ver de qué archivo vino,
    aunque no lo haya subido él. Escritura (subir archivo): ADMIN o
    ADMIN_DIVISION (este, solo a campañas de su división: lo valida el serializer)."""

    serializer_class = LoteCargaSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["campaign", "estado"]
    http_method_names = ["get", "post", "head", "options"]  # append-only: sin edición/borrado

    def get_permissions(self):
        if self.action == "create":
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = LoteCarga.objects.select_related("campaign", "usuario_carga")
        user = self.request.user
        if es_global(user):
            return qs
        return qs.filter(Q(usuario_carga=user) | Q(campaign__in=campanas_visibles_para(user)))

    def perform_create(self, serializer):
        lote = serializer.save()
        procesar_lote_carga.delay(lote.id)
