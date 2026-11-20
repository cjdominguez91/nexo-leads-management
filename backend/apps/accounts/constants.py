from django.db import models


class RoleNames(models.TextChoices):
    """Roles fijos del sistema. No son un catálogo libre: agregar uno nuevo
    requiere también extender apps.core.scoping y las reglas de permisos
    que referencian estos valores explícitamente."""

    ADMIN = "ADMIN", "Administrador"
    GERENTE = "GERENTE", "Gerente"
    SUPERVISOR = "SUPERVISOR", "Supervisor"
    JEFE = "JEFE", "Jefe de agencia"
    SUBJEFE = "SUBJEFE", "Subjefe de agencia"
    EJECUTIVO = "EJECUTIVO", "Ejecutivo"


# Roles con alcance territorial global (sin restricción de agencia/distrito).
GLOBAL_SCOPE_ROLES = (RoleNames.ADMIN, RoleNames.GERENTE)

# Roles que pueden supervisar más de una agencia (relación M2M vía UserAgencia).
MULTI_AGENCIA_ROLES = (RoleNames.JEFE, RoleNames.SUBJEFE)

# Roles que pueden supervisar más de un distrito (relación M2M vía UserTerritorio).
MULTI_TERRITORIO_ROLES = (RoleNames.SUPERVISOR,)
