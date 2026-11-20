import django.db.models.deletion
from django.db import migrations, models


def asignar_division_por_defecto(apps, schema_editor):
    """Las categorías existentes pasan a la primera división (hoy solo existe
    "Red de Agencias")."""
    Category = apps.get_model("leads", "Category")
    Division = apps.get_model("accounts", "Division")
    if not Category.objects.filter(division__isnull=True).exists():
        return
    division = Division.objects.order_by("id").first() or Division.objects.create(nombre="General", codigo="GENERAL")
    Category.objects.filter(division__isnull=True).update(division=division)


class Migration(migrations.Migration):
    dependencies = [
        ("leads", "0008_alter_lead_lote_carga"),
        ("accounts", "0004_seed_admin_division"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="division",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="categorias",
                to="accounts.division",
            ),
        ),
        migrations.RunPython(asignar_division_por_defecto, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="division",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="categorias",
                to="accounts.division",
            ),
        ),
    ]
