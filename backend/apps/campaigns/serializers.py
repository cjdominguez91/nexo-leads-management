from rest_framework import serializers

from .models import (
    SECCION_DATOS_CLIENTE,
    Campaign,
    CampaignFieldDefinition,
    CampaignFieldOrigen,
    CampaignModoCarga,
    CampaignSection,
    CampaignType,
    LoteCarga,
)


class CampaignSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignSection
        fields = ["id", "campaign_type", "nombre", "orden", "es_obligatoria"]
        read_only_fields = ["es_obligatoria"]


class CampaignFieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignFieldDefinition
        fields = [
            "id",
            "campaign_type",
            "field_key",
            "label",
            "data_type",
            "origen",
            "required",
            "options",
            "orden",
            "mostrar_en_tabla",
            "mostrar_en_detalle",
            "seccion",
            "es_nombre_cliente",
            "es_telefono_contacto",
            "es_documento_identidad",
        ]

    def validate(self, attrs):
        data_type = attrs.get("data_type", getattr(self.instance, "data_type", None))
        options = attrs.get("options", getattr(self.instance, "options", None))
        if data_type in ("SELECT", "MULTISELECT") and not options:
            raise serializers.ValidationError({"options": "Requerido para SELECT/MULTISELECT."})

        origen = attrs.get("origen", getattr(self.instance, "origen", CampaignFieldOrigen.CARGA))
        flags_especiales = ("es_nombre_cliente", "es_telefono_contacto", "es_documento_identidad")
        if origen != CampaignFieldOrigen.CARGA:
            for flag in flags_especiales:
                valor = attrs.get(flag, getattr(self.instance, flag, False))
                if valor:
                    raise serializers.ValidationError(
                        {flag: "Solo aplica a campos que se cargan desde el archivo (origen=CARGA)."}
                    )

        campaign_type = attrs.get("campaign_type", getattr(self.instance, "campaign_type", None))
        seccion = attrs.get("seccion", getattr(self.instance, "seccion", None))
        if seccion and campaign_type and seccion.campaign_type_id != campaign_type.id:
            raise serializers.ValidationError({"seccion": "No pertenece al tipo de campaña de este campo."})

        if (
            campaign_type
            and campaign_type.modo_carga == CampaignModoCarga.INDIVIDUAL
            and origen == CampaignFieldOrigen.CAPTURA_GESTION
        ):
            raise serializers.ValidationError(
                {"origen": "Las campañas de Prospección (registro individual) no usan campos de captura."}
            )

        return attrs

    def save(self, **kwargs):
        # A lo sumo un campo por CampaignType puede llevar cada bandera: al
        # marcar una nueva, se destituye a la anterior en vez de rechazar la
        # petición — se comporta como un radio-button, no como una validación.
        campaign_type = self.validated_data.get("campaign_type", getattr(self.instance, "campaign_type", None))
        for flag in ("es_nombre_cliente", "es_telefono_contacto", "es_documento_identidad"):
            if self.validated_data.get(flag) and campaign_type:
                CampaignFieldDefinition.objects.filter(campaign_type=campaign_type, **{flag: True}).exclude(
                    pk=getattr(self.instance, "pk", None)
                ).update(**{flag: False})
        return super().save(**kwargs)


class CampaignTypeSerializer(serializers.ModelSerializer):
    field_definitions = CampaignFieldDefinitionSerializer(many=True, read_only=True)
    secciones = CampaignSectionSerializer(many=True, read_only=True)

    class Meta:
        model = CampaignType
        fields = ["id", "nombre", "categoria", "modo_carga", "secciones", "field_definitions", "created_at", "updated_at"]

    def create(self, validated_data):
        campaign_type = super().create(validated_data)
        CampaignSection.objects.create(
            campaign_type=campaign_type, nombre=SECCION_DATOS_CLIENTE, orden=0, es_obligatoria=True
        )
        return campaign_type


class CampaignSerializer(serializers.ModelSerializer):
    campaign_type_nombre = serializers.CharField(source="campaign_type.nombre", read_only=True)
    campaign_type_modo_carga = serializers.CharField(source="campaign_type.modo_carga", read_only=True)
    division_nombre = serializers.CharField(source="division.nombre", read_only=True)
    esta_cerrada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id",
            "nombre",
            "campaign_type",
            "campaign_type_nombre",
            "campaign_type_modo_carga",
            "division",
            "division_nombre",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "esta_cerrada",
            "producto_default",
            "agencias_habilitadas",
            "distritos_habilitados",
        ]


class LoteCargaSerializer(serializers.ModelSerializer):
    usuario_carga_email = serializers.CharField(source="usuario_carga.email", read_only=True)

    class Meta:
        model = LoteCarga
        fields = [
            "id",
            "campaign",
            "usuario_carga",
            "usuario_carga_email",
            "nombre_archivo",
            "archivo",
            "cantidad_registros",
            "producto",
            "agencia_restriccion",
            "distrito_restriccion",
            "estado",
            "errores",
            "created_at",
        ]
        read_only_fields = ["usuario_carga", "nombre_archivo", "cantidad_registros", "estado", "errores", "created_at"]

    def validate_campaign(self, campaign):
        if campaign.esta_cerrada:
            raise serializers.ValidationError("Esta campaña está cerrada o vencida: no se pueden cargar más leads.")
        if campaign.campaign_type.modo_carga == CampaignModoCarga.INDIVIDUAL:
            raise serializers.ValidationError(
                "Esta es una campaña de Prospección (registro individual): no admite carga de archivos."
            )
        return campaign

    def create(self, validated_data):
        validated_data["nombre_archivo"] = validated_data["archivo"].name
        validated_data["usuario_carga"] = self.context["request"].user
        return super().create(validated_data)
