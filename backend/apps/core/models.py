from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CatalogModel(TimeStampedModel):
    """Base para catálogos administrables por CRUD (Agencia, Territorio, Division, etc.)."""

    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
