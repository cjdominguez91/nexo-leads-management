import django.db.models.deletion
from django.db import migrations, models

SECCION_DATOS_CLIENTE = "Datos del cliente"


def crear_secciones_y_migrar_datos(apps, schema_editor):
    CampaignType = apps.get_model("campaigns", "CampaignType")
    CampaignSection = apps.get_model("campaigns", "CampaignSection")
    CampaignFieldDefinition = apps.get_model("campaigns", "CampaignFieldDefinition")

    for campaign_type in CampaignType.objects.all():
        seccion_default, _ = CampaignSection.objects.get_or_create(
            campaign_type=campaign_type,
            nombre=SECCION_DATOS_CLIENTE,
            defaults={"orden": 0, "es_obligatoria": True},
        )
        secciones_por_nombre = {SECCION_DATOS_CLIENTE: seccion_default}

        for field in CampaignFieldDefinition.objects.filter(campaign_type=campaign_type):
            nombre_legado = (field.seccion_legado or "").strip() or SECCION_DATOS_CLIENTE
            if nombre_legado not in secciones_por_nombre:
                seccion, _ = CampaignSection.objects.get_or_create(
                    campaign_type=campaign_type,
                    nombre=nombre_legado,
                    defaults={"orden": 1},
                )
                secciones_por_nombre[nombre_legado] = seccion
            field.seccion = secciones_por_nombre[nombre_legado]
            field.save(update_fields=["seccion"])


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0004_campaign_agencias_habilitadas_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CampaignSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nombre", models.CharField(max_length=100)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                (
                    "es_obligatoria",
                    models.BooleanField(
                        default=False,
                        help_text="Sección del sistema (ej. 'Datos del cliente'): no se puede eliminar.",
                    ),
                ),
                (
                    "campaign_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="secciones",
                        to="campaigns.campaigntype",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sección",
                "verbose_name_plural": "Secciones",
                "ordering": ["orden", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="campaignsection",
            constraint=models.UniqueConstraint(
                fields=("campaign_type", "nombre"), name="unique_campaign_type_seccion_nombre"
            ),
        ),
        migrations.AddField(
            model_name="campaignfielddefinition",
            name="origen",
            field=models.CharField(
                choices=[("CARGA", "Se carga desde el archivo"), ("CAPTURA_GESTION", "Se captura al gestionar")],
                default="CARGA",
                max_length=20,
            ),
        ),
        migrations.RenameField(
            model_name="campaignfielddefinition",
            old_name="seccion",
            new_name="seccion_legado",
        ),
        migrations.AddField(
            model_name="campaignfielddefinition",
            name="seccion",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="campos",
                to="campaigns.campaignsection",
            ),
        ),
        migrations.RunPython(crear_secciones_y_migrar_datos, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="campaignfielddefinition",
            name="seccion_legado",
        ),
        migrations.AlterField(
            model_name="campaignfielddefinition",
            name="seccion",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="campos",
                to="campaigns.campaignsection",
            ),
        ),
    ]
