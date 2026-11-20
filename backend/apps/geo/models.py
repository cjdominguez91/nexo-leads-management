from django.db import models

from apps.core.models import CatalogModel


class Territorio(CatalogModel):
    """Distrito. Agrupa agencias; es el alcance territorial de SUPERVISOR."""

    codigo = models.CharField(max_length=20, unique=True)

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
