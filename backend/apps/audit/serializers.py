from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.CharField(source="usuario.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "accion",
            "modelo_afectado",
            "id_afectado",
            "datos_antes",
            "datos_despues",
            "timestamp",
            "ip_address",
        ]
        read_only_fields = fields
