from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.mixins import WRITE_ACTIONS
from apps.core.permissions import IsAdmin, IsAdminRole
from apps.core.scoping import es_global, filtrar_por_division

from .constants import ROLES_GESTIONABLES_POR_ADMIN_DIVISION, RoleNames
from .filters import UserFilter
from .models import Division, Role, User, UserAgencia, UserTerritorio
from .serializers import (
    AgenciaAsignacionInputSerializer,
    DivisionSerializer,
    RoleSerializer,
    TerritorioAsignacionInputSerializer,
    UserAgenciaSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserTerritorioSerializer,
)


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo fijo de roles (solo lectura vía API; se administra por
    fixture/migración, no por CRUD — ver apps.accounts.models.Role)."""

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class DivisionViewSet(viewsets.ModelViewSet):
    """Crear/editar divisiones: solo ADMIN global. Un ADMIN_DIVISION puede
    leer, pero solo ve la suya (la necesita para los formularios)."""

    serializer_class = DivisionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo"]

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsAdmin()]
        return [IsAdminRole()]

    def get_queryset(self):
        user = self.request.user
        if es_global(user):
            return Division.objects.all()
        return Division.objects.filter(pk=user.division_id)


class MeView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """Administración de usuarios. Alta/edición/desactivación (nunca borrado
    físico). ADMIN: todos. ADMIN_DIVISION: solo usuarios de su división.

    Un ADMIN_DIVISION ve en el listado a los ADMIN_DIVISION de su división
    (incluido él mismo), pero no puede modificarlos; a los ADMIN globales ni
    siquiera los ve. Las reglas de qué rol/división/agencia puede asignar
    viven en accounts.serializers.validar_alta_o_edicion_usuario.

    Nota: el listado "usuarios visibles dentro de mi scope" para que un
    JEFE/SUPERVISOR elija a quién asignar un lead es otro endpoint, de menor
    privilegio (apps.leads.UsuariosAsignablesViewSet)."""

    permission_classes = [IsAdminRole]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = UserFilter
    ordering_fields = ["email", "first_name", "last_name", "codigo_empleado", "role__nombre", "division__nombre", "is_active", "date_joined"]

    # Acciones que modifican a un usuario existente.
    MODIFY_ACTIONS = ("update", "partial_update", "destroy", "agregar_agencia", "quitar_agencia", "agregar_territorio", "quitar_territorio")

    def get_queryset(self):
        qs = User.objects.select_related("role", "division", "agencia_principal").prefetch_related(
            "agencias_asignadas__agencia", "territorios_asignados__territorio"
        )
        if es_global(self.request.user):
            return qs
        return filtrar_por_division(qs, self.request.user).exclude(role__nombre=RoleNames.ADMIN).exclude(is_superuser=True)

    def get_object(self):
        obj = super().get_object()
        actor = self.request.user
        if (
            self.action in self.MODIFY_ACTIONS
            and not es_global(actor)
            and getattr(obj.role, "nombre", None) not in ROLES_GESTIONABLES_POR_ADMIN_DIVISION
            and obj.role_id is not None
        ):
            raise PermissionDenied("No puedes modificar a un usuario con este rol.")
        return obj

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        # Nunca borrado físico: desactivar, igual que el resto del sistema.
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @staticmethod
    def _validar_division_destino(user, division_id, campo):
        # La agencia/distrito asignado debe ser de la división del usuario
        # (aplica también a ADMIN global: es coherencia de datos, no permiso).
        if user.division_id != division_id:
            raise ValidationError({campo: "No pertenece a la división de este usuario."})

    @action(detail=True, methods=["post"], url_path="agencias")
    def agregar_agencia(self, request, pk=None):
        user = self.get_object()
        serializer = AgenciaAsignacionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agencia = serializer.validated_data["agencia"]
        self._validar_division_destino(user, agencia.territorio.division_id, "agencia")
        asignacion, _ = UserAgencia.objects.update_or_create(
            usuario=user,
            agencia=agencia,
            defaults={"activo": True},
        )
        return Response(UserAgenciaSerializer(asignacion).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="agencias/(?P<agencia_id>[^/.]+)")
    def quitar_agencia(self, request, pk=None, agencia_id=None):
        user = self.get_object()
        UserAgencia.objects.filter(usuario=user, agencia_id=agencia_id, activo=True).update(activo=False)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="territorios")
    def agregar_territorio(self, request, pk=None):
        user = self.get_object()
        serializer = TerritorioAsignacionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        territorio = serializer.validated_data["territorio"]
        self._validar_division_destino(user, territorio.division_id, "territorio")
        asignacion, _ = UserTerritorio.objects.update_or_create(
            usuario=user,
            territorio=territorio,
            defaults={"activo": True},
        )
        return Response(UserTerritorioSerializer(asignacion).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="territorios/(?P<territorio_id>[^/.]+)")
    def quitar_territorio(self, request, pk=None, territorio_id=None):
        user = self.get_object()
        UserTerritorio.objects.filter(
            usuario=user, territorio_id=territorio_id, activo=True
        ).update(activo=False)
        return Response(status=status.HTTP_204_NO_CONTENT)
