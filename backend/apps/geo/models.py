from django.db import models

from apps.core.models import CatalogModel


class Territorio(CatalogModel):
    """Distrito. Agrupa agencias; es el alcance territorial de SUPERVISOR.

    Pertenece a una División. La Agencia NO tiene FK propia a División: la
    hereda de su distrito (agencia.territorio.division), así es imposible que
    una agencia y su distrito queden en divisiones distintas."""

    codigo = models.CharField(max_length=20, unique=True)
    division = models.ForeignKey("accounts.Division", on_delete=models.PROTECT, related_name="territorios")

    class Meta(CatalogModel.Meta):
        verbose_name = "Territorio"
        verbose_name_plural = "Territorios"


class Agencia(CatalogModel):
    """Agencia (codAge). Es el alcance territorial de JEFE/SUBJEFE y la
    unidad a la que pertenece un EJECUTIVO."""

    codigo = models.CharField(max_length=20, unique=True)
    territorio = models.ForeignKey(
        Territorio,
        on_delete=models.PROTECT,
        related_name="agencias",
    )

    class Meta(CatalogModel.Meta):
        verbose_name = "Agencia"
        verbose_name_plural = "Agencias"
