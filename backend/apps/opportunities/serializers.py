from rest_framework import serializers

from .models import Opportunity


class OpportunitySerializer(serializers.ModelSerializer):
    campaign_nombre = serializers.CharField(source="campaign.nombre", read_only=True)
    cliente_nombre = serializers.CharField(source="lead.cliente_nombre", read_only=True)
    documento_identidad = serializers.CharField(source="lead.documento_identidad", read_only=True)
    categoria_actual_nombre = serializers.CharField(source="lead.categoria_actual.nombre", read_only=True, default=None)
    subcategoria_actual_nombre = serializers.CharField(
        source="lead.subcategoria_actual.nombre", read_only=True, default=None
    )
    usuario_responsable_email = serializers.CharField(source="usuario_responsable.email", read_only=True)
    modo_carga = serializers.CharField(source="campaign.campaign_type.modo_carga", read_only=True)

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "lead",
            "cliente_nombre",
            "documento_identidad",
            "campaign",
            "campaign_nombre",
            "modo_carga",
            "categoria_actual_nombre",
            "subcategoria_actual_nombre",
            "usuario_responsable",
            "usuario_responsable_email",
            "prioridad",
            "estado",
            "fecha_cierre",
            "fecha_proximo_contacto",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "lead",
            "campaign",
            "usuario_responsable",
            "estado",
            "fecha_cierre",
            "fecha_proximo_contacto",
            "created_at",
            "updated_at",
        ]


class OpportunityPrioridadInputSerializer(serializers.Serializer):
    prioridad = serializers.ChoiceField(choices=["ALTA", "MEDIA", "BAJA"])
