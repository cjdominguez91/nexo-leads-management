from rest_framework import serializers

from apps.core.mixins import DivisionOwnedSerializerMixin, validar_en_division

from .models import Agencia, Territorio


class TerritorioSerializer(DivisionOwnedSerializerMixin, serializers.ModelSerializer):
    division_nombre = serializers.CharField(source="division.nombre", read_only=True)

    class Meta:
        model = Territorio
        fields = ["id", "nombre", "codigo", "division", "division_nombre", "activo", "created_at", "updated_at"]


class AgenciaSerializer(serializers.ModelSerializer):
    territorio_nombre = serializers.CharField(source="territorio.nombre", read_only=True)
    # Derivada del distrito (solo lectura): la agencia no tiene FK propia a División.
    division = serializers.IntegerField(source="territorio.division_id", read_only=True)
    division_nombre = serializers.CharField(source="territorio.division.nombre", read_only=True)

    class Meta:
        model = Agencia
        fields = [
            "id",
            "nombre",
            "codigo",
            "territorio",
            "territorio_nombre",
            "division",
            "division_nombre",
            "activo",
            "created_at",
            "updated_at",
        ]

    def validate_territorio(self, territorio):
        validar_en_division(self.context["request"], territorio.division_id, "territorio", "Ese distrito no es de tu división.")
        # Cambiar el distrito sí se permite, pero no a uno de otra división:
        # la agencia arrastraría sus leads/usuarios a una división ajena.
        if self.instance is not None and territorio.division_id != self.instance.territorio.division_id:
            raise serializers.ValidationError("No se puede mover una agencia a un distrito de otra división.")
        return territorio
