"""Piezas reutilizables para aislar catálogos por División.

Dos capas, y hacen falta las dos:

- DivisionScopedViewSetMixin (vista): el queryset solo contiene registros de
  la división del usuario. Un ADMIN_DIVISION no puede leer, editar ni borrar
  algo de otra división porque para él ese registro simplemente no existe
  (responde 404, no 403: no revela que el id existe en otra división).

- DivisionOwnedSerializerMixin / validar_en_division (serializer): al CREAR
  o al apuntar a un padre (agencia→distrito, subcategoría→categoría), valida
  que lo que llega en el body también sea de su división. El queryset no
  protege esto: el id del padre viene en el JSON, no en la URL.
"""

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated

from .permissions import IsAdminRole
from .scoping import es_global, filtrar_por_division, misma_division

WRITE_ACTIONS = ("create", "update", "partial_update", "destroy")


class DivisionScopedViewSetMixin:
    """Lectura: cualquier autenticado, solo su división. Escritura: ADMIN o
    ADMIN_DIVISION (este último, de nuevo, solo dentro de su división).

    `division_lookup` = camino desde el modelo hasta Division, ej.
    "division", "territorio__division", "category__division"."""

    division_lookup = "division"

    def get_permissions(self):
        if self.action in WRITE_ACTIONS:
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return filtrar_por_division(super().get_queryset(), self.request.user, self.division_lookup)


def validar_en_division(request, division_id, campo: str, mensaje: str | None = None):
    """Lanza ValidationError si `request.user` no puede operar en `division_id`."""
    if not misma_division(request.user, division_id):
        raise serializers.ValidationError({campo: mensaje or "No pertenece a tu división."})


class DivisionOwnedSerializerMixin:
    """Para modelos con FK directa `division` (Territorio, CampaignType, Category).

    - ADMIN global: debe elegir la división al crear.
    - ADMIN_DIVISION: la división se fija a la suya; lo que mande se ignora.
    - Nadie puede cambiar la división de un registro existente: movería con
      él agencias, campañas o tipificaciones históricas a otra división."""

    def get_fields(self):
        fields = super().get_fields()
        fields["division"].required = False
        return fields

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context["request"]
        if self.instance is not None:
            if "division" in attrs and attrs["division"].id != self.instance.division_id:
                raise serializers.ValidationError({"division": "La división no se puede cambiar una vez creado."})
            return attrs
        if not es_global(request.user):
            attrs["division"] = request.user.division
        if not attrs.get("division"):
            raise serializers.ValidationError({"division": "Este campo es obligatorio."})
        return attrs
