from rest_framework import serializers

from .models import Agencia, Territorio


class TerritorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Territorio
        fields = ["id", "nombre", "codigo", "activo", "created_at", "updated_at"]


class AgenciaSerializer(serializers.ModelSerializer):
    territorio_nombre = serializers.CharField(source="territorio.nombre", read_only=True)

    class Meta:
        model = Agencia
        fields = [
            "id",
            "nombre",
            "codigo",
            "territorio",
            "territorio_nombre",
            "activo",
            "created_at",
            "updated_at",
        ]
