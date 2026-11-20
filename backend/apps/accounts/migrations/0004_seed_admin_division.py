from django.db import migrations

# Inserta ADMIN_DIVISION entre ADMIN y GERENTE y corre los niveles de abajo.
# nivel_jerarquico solo se usa para ordenar (no en reglas de permisos).
NIVELES = {
    "ADMIN": 1,
    "ADMIN_DIVISION": 2,
    "GERENTE": 3,
    "SUPERVISOR": 4,
    "JEFE": 5,
    "SUBJEFE": 5,
    "EJECUTIVO": 6,
}
NIVELES_ANTERIORES = {"ADMIN": 1, "GERENTE": 2, "SUPERVISOR": 3, "JEFE": 4, "SUBJEFE": 4, "EJECUTIVO": 5}


def seed(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.update_or_create(
        nombre="ADMIN_DIVISION",
        defaults={
            "nivel_jerarquico": NIVELES["ADMIN_DIVISION"],
            "descripcion": "Administra usuarios, agencias, distritos, tipos de campaña y catálogos de su división.",
        },
    )
    Role.objects.filter(nombre="GERENTE").update(descripcion="Lectura/gestión amplia dentro de su división.")
    for nombre, nivel in NIVELES.items():
        Role.objects.filter(nombre=nombre).update(nivel_jerarquico=nivel)


def unseed(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(nombre="ADMIN_DIVISION").delete()
    for nombre, nivel in NIVELES_ANTERIORES.items():
        Role.objects.filter(nombre=nombre).update(nivel_jerarquico=nivel)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_user_codigo_empleado")]

    operations = [migrations.RunPython(seed, unseed)]
