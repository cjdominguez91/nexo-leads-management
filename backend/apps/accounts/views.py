from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.permissions import IsAdmin

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
    queryset = Division.objects.all()
    serializer_class = DivisionSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["activo"]


class MeView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(UserSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """Administración de usuarios. Alta/edición/desactivación (nunca borrado
    físico) — solo ADMIN, según sección 5.0 del prompt de arquitectura.

    Nota: el listado "usuarios visibles dentro de mi scope" para que un
    JEFE/SUPERVISOR elija a quién asignar un lead es un endpoint distinto,
    de menor privilegio, que se agrega en la Fase 2 (apps.leads) reusando
    apps.core.scoping.usuarios_visibles_para — no se mezcla con esta
    administración, que es exclusivamente de ADMIN."""

    queryset = User.objects.select_related("role", "division", "agencia_principal").prefetch_related(
        "agencias_asignadas__agencia", "territorios_asignados__territorio"
    )
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = UserFilter
    ordering_fields = ["email", "first_name", "last_name", "codigo_empleado", "role__nombre", "division__nombre", "is_active", "date_joined"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        # Nunca borrado físico: desactivar, igual que el resto del sistema.
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=True, methods=["post"], url_path="agencias")
    def agregar_agencia(self, request, pk=None):
        user = self.get_object()
        serializer = AgenciaAsignacionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asignacion, _ = UserAgencia.objects.update_or_create(
            usuario=user,
            agencia=serializer.validated_data["agencia"],
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
        asignacion, _ = UserTerritorio.objects.update_or_create(
            usuario=user,
            territorio=serializer.validated_data["territorio"],
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
