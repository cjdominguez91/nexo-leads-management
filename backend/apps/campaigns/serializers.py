from rest_framework import serializers

from apps.core.mixins import DivisionOwnedSerializerMixin, validar_en_division
from apps.core.scoping import campanas_visibles_para, es_global

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


def _validar_campaign_type(serializer, campaign_type):
    """Secciones y campos cuelgan de un CampaignType: debe ser de la división
    de quien escribe, y no se puede mover a un tipo de otra división."""
    validar_en_division(serializer.context["request"], campaign_type.division_id, "campaign_type")
    if serializer.instance is not None and campaign_type.division_id != serializer.instance.campaign_type.division_id:
        raise serializers.ValidationError("No se puede mover a un tipo de campaña de otra división.")
    return campaign_type


class CampaignSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignSection
        fields = ["id", "campaign_type", "nombre", "orden", "es_obligatoria"]
        read_only_fields = ["es_obligatoria"]

    def validate_campaign_type(self, campaign_type):
        return _validar_campaign_type(self, campaign_type)


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

    def validate_campaign_type(self, campaign_type):
        return _validar_campaign_type(self, campaign_type)

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


class CampaignTypeSerializer(DivisionOwnedSerializerMixin, serializers.ModelSerializer):
    field_definitions = CampaignFieldDefinitionSerializer(many=True, read_only=True)
    secciones = CampaignSectionSerializer(many=True, read_only=True)
    division_nombre = serializers.CharField(source="division.nombre", read_only=True)

    class Meta:
        model = CampaignType
        fields = [
            "id",
            "nombre",
            "division",
            "division_nombre",
            "categoria",
            "modo_carga",
            "secciones",
            "field_definitions",
            "created_at",
            "updated_at",
        ]
        # El UniqueConstraint (division, nombre) se valida a mano en validate():
        # el validador automático de DRF exigiría `division` en el body, y para
        # un ADMIN_DIVISION la división no viene del body, se fija a la suya.
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        division = attrs.get("division") or self.instance.division
        nombre = attrs.get("nombre", getattr(self.instance, "nombre", None))
        repetido = CampaignType.objects.filter(division=division, nombre__iexact=nombre)
        if self.instance is not None:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise serializers.ValidationError({"nombre": "Ya existe un tipo de campaña con ese nombre en esta división."})
        return attrs

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

    def get_fields(self):
        fields = super().get_fields()
        fields["division"].required = False
        return fields

    def validate(self, attrs):
        """Todo lo que referencia una campaña debe ser de su misma división:
        tipo, agencias y distritos habilitados. Un ADMIN_DIVISION crea
        siempre en la suya; la división de una campaña existente no cambia."""
        request = self.context["request"]
        user = request.user

        if self.instance is not None:
            if "division" in attrs and attrs["division"].id != self.instance.division_id:
                raise serializers.ValidationError({"division": "La división no se puede cambiar una vez creada."})
            division = self.instance.division
        else:
            if es_global(user):
                division = attrs.get("division")
            else:
                division = user.division
                attrs["division"] = division
            if division is None:
                raise serializers.ValidationError({"division": "Este campo es obligatorio."})
        validar_en_division(request, division.id, "division")

        campaign_type = attrs.get("campaign_type", getattr(self.instance, "campaign_type", None))
        if campaign_type and campaign_type.division_id != division.id:
            raise serializers.ValidationError({"campaign_type": "El tipo de campaña es de otra división."})
        for agencia in attrs.get("agencias_habilitadas", []):
            if agencia.territorio.division_id != division.id:
                raise serializers.ValidationError({"agencias_habilitadas": f"'{agencia.nombre}' es de otra división."})
        for territorio in attrs.get("distritos_habilitados", []):
            if territorio.division_id != division.id:
                raise serializers.ValidationError({"distritos_habilitados": f"'{territorio.nombre}' es de otra división."})
        return attrs


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

    def validate(self, attrs):
        """Las restricciones del lote deben ser de la división de la campaña:
        si no, los leads quedarían en una agencia que nadie de esa división ve."""
        attrs = super().validate(attrs)
        division_id = attrs["campaign"].division_id
        agencia = attrs.get("agencia_restriccion")
        distrito = attrs.get("distrito_restriccion")
        if agencia and agencia.territorio.division_id != division_id:
            raise serializers.ValidationError({"agencia_restriccion": "Esa agencia es de otra división."})
        if distrito and distrito.division_id != division_id:
            raise serializers.ValidationError({"distrito_restriccion": "Ese distrito es de otra división."})
        return attrs

    def validate_campaign(self, campaign):
        # El id de la campaña viene en el body: hay que comprobar el alcance
        # aquí, el queryset del viewset no lo cubre en un POST.
        user = self.context["request"].user
        if not campanas_visibles_para(user).filter(pk=campaign.pk).exists():
            raise serializers.ValidationError("Esa campaña está fuera de tu alcance.")
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
