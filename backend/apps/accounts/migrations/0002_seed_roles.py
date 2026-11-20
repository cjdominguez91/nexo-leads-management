from django.db import migrations

from apps.accounts.constants import RoleNames

ROLES = [
    (RoleNames.ADMIN, 1, "Acceso total, gestión de usuarios."),
    (RoleNames.GERENTE, 2, "Alcance global, solo lectura/gestión amplia."),
    (RoleNames.SUPERVISOR, 3, "Alcance por distrito(s)."),
    (RoleNames.JEFE, 4, "Alcance por agencia(s)."),
    (RoleNames.SUBJEFE, 4, "Alcance por agencia(s), igual que JEFE."),
    (RoleNames.EJECUTIVO, 5, "Solo sus propios leads asignados."),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for nombre, nivel, descripcion in ROLES:
        Role.objects.update_or_create(
            nombre=nombre,
            defaults={"nivel_jerarquico": nivel, "descripcion": descripcion},
        )


def unseed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(nombre__in=[r[0] for r in ROLES]).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [migrations.RunPython(seed_roles, unseed_roles)]
