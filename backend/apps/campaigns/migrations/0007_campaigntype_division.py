import django.db.models.deletion
from django.db import migrations, models


def asignar_division(apps, schema_editor):
    """Cada tipo existente toma la división de sus campañas (hoy todas son de
    "Red de Agencias"). Un tipo sin campañas toma la primera división."""
    CampaignType = apps.get_model("campaigns", "CampaignType")
    Campaign = apps.get_model("campaigns", "Campaign")
    Division = apps.get_model("accounts", "Division")
    pendientes = CampaignType.objects.filter(division__isnull=True)
    if not pendientes.exists():
        return
    por_defecto = Division.objects.order_by("id").first() or Division.objects.create(nombre="General", codigo="GENERAL")
    for ct in pendientes:
        division_ids = set(Campaign.objects.filter(campaign_type=ct).values_list("division_id", flat=True))
        if len(division_ids) > 1:
            raise RuntimeError(
                f"El tipo de campaña '{ct.nombre}' se usa en varias divisiones; hay que duplicarlo por división a mano antes de migrar."
            )
        ct.division_id = division_ids.pop() if division_ids else por_defecto.id
        ct.save(update_fields=["division"])


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0006_campaigntype_modo_carga"),
        ("accounts", "0004_seed_admin_division"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaigntype",
            name="division",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="campaign_types",
                to="accounts.division",
            ),
        ),
        migrations.RunPython(asignar_division, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="campaigntype",
            name="division",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="campaign_types",
                to="accounts.division",
            ),
        ),
        migrations.AlterField(
            model_name="campaigntype",
            name="nombre",
            field=models.CharField(max_length=150),
        ),
        migrations.AddConstraint(
            model_name="campaigntype",
            constraint=models.UniqueConstraint(fields=("division", "nombre"), name="unique_campaigntype_division_nombre"),
        ),
    ]
