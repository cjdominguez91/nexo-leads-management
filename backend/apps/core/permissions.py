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
    allowed_roles = (RoleNames.ADMIN,)


class IsAdminOrGerente(RoleRequired):
    allowed_roles = (RoleNames.ADMIN, RoleNames.GERENTE)


class IsSupervisionRole(RoleRequired):
    """ADMIN/GERENTE globales + SUPERVISOR/JEFE/SUBJEFE dentro de su scope territorial."""

    allowed_roles = (
        RoleNames.ADMIN,
        RoleNames.GERENTE,
        RoleNames.SUPERVISOR,
        RoleNames.JEFE,
        RoleNames.SUBJEFE,
    )
