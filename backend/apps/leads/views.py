from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.constants import GLOBAL_SCOPE_ROLES, RoleNames
from apps.campaigns.validators import AtributosValidationError
from apps.core.permissions import IsAdmin, IsSupervisionRole
from apps.core.scoping import agencias_visibles_para, campanas_visibles_para, usuarios_visibles_para

from .filters import LeadFilter
from .models import Assignment, Category, Lead, SubCategory
from .serializers import (
    AsignarLeadInputSerializer,
    AsignarMasivoInputSerializer,
    AssignmentSerializer,
    CaptureEntrySerializer,
    CategorySerializer,
    CrearProspectoInputSerializer,
    GestionarLeadInputSerializer,
    LeadSerializer,
    ManagementLogSerializer,
    SubCategorySerializer,
    UsuarioAsignableSerializer,
)
from apps.notifications.services import notificar_asignacion

from .services import (
    AssignmentError,
    ProspectoError,
    ProspectoYaExisteError,
    crear_prospecto,
    leads_visibles_para,
    reasignar_lead,
    tipificar_lead,
)


def _role(user):
    return getattr(user.role, "nombre", None) if getattr(user, "role_id", None) else None


class CategoryViewSet(viewsets.ModelViewSet):
    """Lectura: cualquier usuario autenticado — quien tipifica un lead
    necesita leer este catálogo. Escritura: solo ADMIN."""

    queryset = Category.objects.prefetch_related("subcategorias")
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


class SubCategoryViewSet(viewsets.ModelViewSet):
    """Mismo criterio que CategoryViewSet: lectura abierta, escritura ADMIN."""

    queryset = SubCategory.objects.select_related("category")
    serializer_class = SubCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "activo"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]


class UsuariosAsignablesViewSet(viewsets.ReadOnlyModelViewSet):
    """Usuarios dentro del alcance de quien pregunta — no es la
    administración de cuentas (esa es apps.accounts, solo ADMIN), es el
    listado liviano que un JEFE/SUPERVISOR necesita para elegir a quién
    asignarle un lead."""

    serializer_class = UsuarioAsignableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return usuarios_visibles_para(self.request.user).select_related("role", "agencia_principal")


class LeadViewSet(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Solo lectura (más create, exclusivo para Prospección) + acciones de
    dominio: asignar/custodia, gestionar/evolucion/capturas."""

    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = LeadFilter
    ordering_fields = [
        "created_at",
        "documento_identidad",
        "cliente_nombre",
        "estado",
        "fecha_asignacion",
        "fecha_ultima_gestion",
        "usuario_asignado__email",
        "agencia__nombre",
    ]

    # Prefijo de query param para filtrar por un campo de `atributos` (JSONB) —
    # varían por CampaignType así que no se pueden declarar como campos fijos
    # en LeadFilter. ej. ?attr__monto_oferta=1000 -> atributos__monto_oferta__icontains=1000
    ATTR_FILTER_PREFIX = "attr__"

    def get_queryset(self):
        qs = leads_visibles_para(self.request.user).select_related(
            "campaign__campaign_type",
            "agencia",
            "distrito",
            "usuario_asignado",
            "categoria_actual",
            "subcategoria_actual",
        )
        for param, value in self.request.query_params.items():
            if param.startswith(self.ATTR_FILTER_PREFIX) and value:
                field_key = param[len(self.ATTR_FILTER_PREFIX) :]
                qs = qs.filter(**{f"atributos__{field_key}__icontains": value})
        return qs

    # Acciones de "ver el detalle de un lead" — a propósito NO incluye
    # "asignar" (la reasignación sigue permitida en campañas cerradas, ver
    # el aviso en CampaignDetailView) ni "gestionar" (esa ya se bloquea para
    # todos los roles, cerrada o no, con su propio chequeo más abajo).
    DETAIL_ACTIONS = ("retrieve", "custodia", "evolucion", "capturas", "oportunidad")

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if (
            self.action in self.DETAIL_ACTIONS
            and obj.campaign.esta_cerrada
            and not user.is_superuser
            and _role(user) not in GLOBAL_SCOPE_ROLES
        ):
            raise PermissionDenied(
                "Esta campaña está cerrada — el detalle de este registro ya no está disponible para tu rol."
            )
        return obj

    def get_permissions(self):
        # EJECUTIVO tipifica sus leads, no asigna (ver tabla de roles del prompt de arquitectura).
        if self.action in ("asignar", "asignar_masivo"):
            return [IsSupervisionRole()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Registro individual de un prospecto — exclusivo de campañas con
        campaign_type.modo_carga=INDIVIDUAL ("Prospección"). Cualquier rol
        autenticado puede registrar, siempre que la campaña esté dentro de
        su alcance (ver apps.core.scoping.campanas_visibles_para)."""

        serializer = CrearProspectoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.validated_data["campaign"]
        agencia = serializer.validated_data.get("agencia")
        atributos = serializer.validated_data["atributos"]

        user = request.user
        if not (
            user.is_superuser
            or campaign.id in campanas_visibles_para(user).values_list("id", flat=True)
        ):
            return Response({"detail": "Esta campaña está fuera de tu alcance."}, status=status.HTTP_403_FORBIDDEN)

        try:
            lead, reclamado = crear_prospecto(
                campaign=campaign, usuario=user, atributos_raw=atributos, agencia=agencia
            )
        except ProspectoError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except AtributosValidationError as exc:
            return Response({"atributos": exc.errors}, status=status.HTTP_400_BAD_REQUEST)
        except ProspectoYaExisteError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "lead_id": exc.lead.id,
                    "usuario_asignado_email": (
                        exc.lead.usuario_asignado.email if exc.lead.usuario_asignado else None
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {"lead": LeadSerializer(lead).data, "reclamado": reclamado},
            status=status.HTTP_200_OK if reclamado else status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="asignar")
    def asignar(self, request, pk=None):
        lead = self.get_object()
        serializer = AsignarLeadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = reasignar_lead(
                lead=lead,
                usuario_destino=serializer.validated_data["usuario_destino"],
                asignado_por=request.user,
            )
        except AssignmentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(AssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="asignar-masivo")
    def asignar_masivo(self, request):
        """Una sola notificación agregada al final ("N registros de la
        campaña X te fueron asignados"), no una por lead — por eso
        reasignar_lead se llama con notificar=False y se agrupa acá."""

        serializer = AsignarMasivoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario_destino = serializer.validated_data["usuario_destino"]
        lead_ids = serializer.validated_data["lead_ids"]

        leads = self.get_queryset().filter(id__in=lead_ids).select_related("campaign__campaign_type")
        leads_by_id = {lead.id: lead for lead in leads}

        resultados = []
        campanas_exitosas: dict[int, object] = {}
        for lead_id in lead_ids:
            lead = leads_by_id.get(lead_id)
            if lead is None:
                resultados.append({"lead_id": lead_id, "ok": False, "error": "Fuera de tu alcance o no existe."})
                continue
            try:
                reasignar_lead(lead=lead, usuario_destino=usuario_destino, asignado_por=request.user, notificar=False)
                resultados.append({"lead_id": lead_id, "ok": True})
                campanas_exitosas[lead.campaign_id] = lead.campaign
            except AssignmentError as exc:
                resultados.append({"lead_id": lead_id, "ok": False, "error": str(exc)})

        for campaign_id, campaign in campanas_exitosas.items():
            cantidad = sum(1 for r in resultados if r["ok"] and leads_by_id[r["lead_id"]].campaign_id == campaign_id)
            notificar_asignacion(
                usuario_destino_id=usuario_destino.id, campaign=campaign, cantidad=cantidad, motivo="asignación masiva"
            )

        return Response({"resultados": resultados})

    @action(detail=True, methods=["get"], url_path="custodia")
    def custodia(self, request, pk=None):
        lead = self.get_object()
        historial = lead.historial_asignaciones.select_related(
            "usuario_origen", "usuario_destino", "agencia_origen", "agencia_destino", "asignado_por"
        )
        return Response(AssignmentSerializer(historial, many=True).data)

    @action(detail=True, methods=["post"], url_path="gestionar")
    def gestionar(self, request, pk=None):
        """Tipificación. No exclusiva de EJECUTIVO: SUPERVISOR/JEFE/SUBJEFE
        también pueden gestionar cualquier lead dentro de su scope.

        Control de propiedad al momento de escribir: se relee el lead
        directo de la base (no del queryset cacheado del frontend) — si un
        EJECUTIVO ya no es el usuario_asignado actual (lo reasignaron
        mientras tenía la pantalla abierta), se rechaza con 409 e informa
        quién es el nuevo responsable, en vez de dejarlo guardar a ciegas."""

        lead = get_object_or_404(
            Lead.objects.select_related("usuario_asignado", "agencia", "campaign"), pk=pk
        )
        user = request.user
        role = _role(user)

        if lead.campaign.esta_cerrada:
            return Response(
                {"detail": "Esta campaña está cerrada o vencida: ya no se pueden registrar gestiones."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (user.is_superuser or role in GLOBAL_SCOPE_ROLES):
            if role == RoleNames.EJECUTIVO:
                if lead.usuario_asignado_id != user.id:
                    return Response(
                        {
                            "detail": "Este registro ya no te pertenece, fue reasignado.",
                            "usuario_asignado_email": (
                                lead.usuario_asignado.email if lead.usuario_asignado else None
                            ),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
            elif lead.agencia_id not in agencias_visibles_para(user).values_list("id", flat=True):
                return Response(
                    {"detail": "Este lead está fuera de tu alcance."}, status=status.HTTP_403_FORBIDDEN
                )

        serializer = GestionarLeadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            log, opportunity = tipificar_lead(
                lead=lead,
                usuario=user,
                category=serializer.validated_data["category"],
                subcategory=serializer.validated_data.get("subcategory"),
                comentario=serializer.validated_data["comentario"],
                fecha_proximo_contacto=serializer.validated_data.get("fecha_proximo_contacto"),
                datos_captura=serializer.validated_data.get("datos_captura"),
            )
        except AtributosValidationError as exc:
            return Response({"datos_captura": exc.errors}, status=status.HTTP_400_BAD_REQUEST)

        from apps.opportunities.serializers import OpportunitySerializer

        return Response(
            {
                "log": ManagementLogSerializer(log).data,
                "opportunity": OpportunitySerializer(opportunity).data if opportunity else None,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="evolucion")
    def evolucion(self, request, pk=None):
        lead = self.get_object()
        gestiones = lead.gestiones.select_related("usuario", "category", "subcategory")
        return Response(ManagementLogSerializer(gestiones, many=True).data)

    @action(detail=True, methods=["get"], url_path="capturas")
    def capturas(self, request, pk=None):
        lead = self.get_object()
        historial = lead.capturas.select_related("usuario")
        return Response(CaptureEntrySerializer(historial, many=True).data)

    @action(detail=True, methods=["get"], url_path="oportunidad")
    def oportunidad(self, request, pk=None):
        """La oportunidad vigente de este lead (la última creada), si existe.
        Usado por el panel de "Oportunidad" en el detalle del lead — ya no
        hay una vista de detalle de oportunidad aparte."""
        from apps.opportunities.models import Opportunity
        from apps.opportunities.serializers import OpportunitySerializer

        lead = self.get_object()
        opportunity = (
            Opportunity.objects.filter(lead=lead)
            .select_related("lead__categoria_actual", "lead__subcategoria_actual", "campaign", "usuario_responsable")
            .order_by("-created_at")
            .first()
        )
        return Response(OpportunitySerializer(opportunity).data if opportunity else None)
