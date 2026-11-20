import django.db.models.deletion
from django.db import migrations, models


def asignar_division_por_defecto(apps, schema_editor):
    """Los distritos existentes pasan a la primera división (hoy solo existe
    "Red de Agencias"). Si hubiera distritos sin ninguna división creada, se
    crea una "General" para no romper la migración."""
    Territorio = apps.get_model("geo", "Territorio")
    Division = apps.get_model("accounts", "Division")
    if not Territorio.objects.filter(division__isnull=True).exists():
        return
    division = Division.objects.order_by("id").first() or Division.objects.create(nombre="General", codigo="GENERAL")
    Territorio.objects.filter(division__isnull=True).update(division=division)


class Migration(migrations.Migration):
    dependencies = [
        ("geo", "0001_initial"),
        ("accounts", "0004_seed_admin_division"),
    ]

    operations = [
        migrations.AddField(
            model_name="territorio",
            name="division",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="territorios",
                to="accounts.division",
            ),
        ),
        migrations.RunPython(asignar_division_por_defecto, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="territorio",
            name="division",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="territorios",
                to="accounts.division",
            ),
        ),
    ]
