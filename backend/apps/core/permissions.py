from rest_framework.permissions import BasePermission

from apps.accounts.constants import RoleNames


def _role(request):
    user = request.user
    if not (user and user.is_authenticated):
        return None
    return getattr(user.role, "nombre", None) if user.role_id else None


class RoleRequired(BasePermission):
    """Permission base parametrizable por rol. Uso: `RoleRequired.roles(("ADMIN",))`."""

    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        if request.user and request.user.is_superuser:
            return True
        return _role(request) in self.allowed_roles

    @classmethod
    def roles(cls, allowed_roles):
        return type("RoleRequired", (cls,), {"allowed_roles": tuple(allowed_roles)})


class IsAdmin(RoleRequired):
    """Solo ADMIN global. Para lo que cruza divisiones (ej. CRUD de Division)."""

    allowed_roles = (RoleNames.ADMIN,)


class IsAdminRole(RoleRequired):
    """ADMIN o ADMIN_DIVISION. Este permiso solo responde "¿es un rol de
    administración?"; que un ADMIN_DIVISION no toque otra división lo
    garantiza el queryset (apps.core.scoping.filtrar_por_division) más la
    validación del serializer. Nunca usar esto solo, sin el filtro."""

    allowed_roles = (RoleNames.ADMIN, RoleNames.ADMIN_DIVISION)


class IsAdminOrGerente(RoleRequired):
    """Lectura amplia (auditoría). GERENTE y ADMIN_DIVISION, solo de su división."""

    allowed_roles = (RoleNames.ADMIN, RoleNames.ADMIN_DIVISION, RoleNames.GERENTE)


class IsSupervisionRole(RoleRequired):
    """Roles que asignan leads, cada uno dentro de su alcance."""

    allowed_roles = (
        RoleNames.ADMIN,
        RoleNames.ADMIN_DIVISION,
        RoleNames.GERENTE,
        RoleNames.SUPERVISOR,
        RoleNames.JEFE,
        RoleNames.SUBJEFE,
    )
