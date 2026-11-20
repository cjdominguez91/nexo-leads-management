from django.db import models


class RoleNames(models.TextChoices):
    """Roles fijos del sistema. No son un catálogo libre: agregar uno nuevo
    requiere también extender apps.core.scoping y las reglas de permisos
    que referencian estos valores explícitamente."""

    ADMIN = "ADMIN", "Administrador"
    ADMIN_DIVISION = "ADMIN_DIVISION", "Administrador de división"
    GERENTE = "GERENTE", "Gerente"
    SUPERVISOR = "SUPERVISOR", "Supervisor"
    JEFE = "JEFE", "Jefe de agencia"
    SUBJEFE = "SUBJEFE", "Subjefe de agencia"
    EJECUTIVO = "EJECUTIVO", "Ejecutivo"


# Alcance en dos ejes independientes:
#   1. División: ¿ve todas las divisiones o solo la suya?
#   2. Territorio: dentro de su división, ¿ve todas las agencias o solo las suyas?
#
# Solo ADMIN (y superusuario) cruza divisiones. ADMIN_DIVISION y GERENTE ven
# todo el territorio, pero de su propia división. El resto, su territorio.
GLOBAL_SCOPE_ROLES = (RoleNames.ADMIN,)

# Sin restricción territorial dentro de su división.
DIVISION_SCOPE_ROLES = (RoleNames.ADMIN_DIVISION, RoleNames.GERENTE)

# Administran catálogos/usuarios/campañas (ADMIN en todas, ADMIN_DIVISION en la suya).
ADMIN_ROLES = (RoleNames.ADMIN, RoleNames.ADMIN_DIVISION)

# Roles que un ADMIN_DIVISION puede crear/editar. No incluye ADMIN ni
# ADMIN_DIVISION: evita que un admin de división se auto-escale o cree pares.
ROLES_GESTIONABLES_POR_ADMIN_DIVISION = (
    RoleNames.GERENTE,
    RoleNames.SUPERVISOR,
    RoleNames.JEFE,
    RoleNames.SUBJEFE,
    RoleNames.EJECUTIVO,
)

# Roles que pueden supervisar más de una agencia (relación M2M vía UserAgencia).
MULTI_AGENCIA_ROLES = (RoleNames.JEFE, RoleNames.SUBJEFE)

# Roles que pueden supervisar más de un distrito (relación M2M vía UserTerritorio).
MULTI_TERRITORIO_ROLES = (RoleNames.SUPERVISOR,)
