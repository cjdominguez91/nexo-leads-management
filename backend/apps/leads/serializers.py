from rest_framework import serializers

from apps.accounts.models import User
from apps.campaigns.models import Campaign
from apps.core.mixins import DivisionOwnedSerializerMixin, validar_en_division
from apps.geo.models import Agencia

from .models import Assignment, CaptureEntry, Category, Lead, ManagementLog, SubCategory


class UsuarioAsignableSerializer(serializers.ModelSerializer):
    role_nombre = serializers.CharField(source="role.nombre", read_only=True, default=None)
    agencia_principal_nombre = serializers.CharField(
        source="agencia_principal.nombre", read_only=True, default=None
    )

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role_nombre", "division", "agencia_principal_nombre"]


class CategorySerializer(DivisionOwnedSerializerMixin, serializers.ModelSerializer):
    division_nombre = serializers.CharField(source="division.nombre", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "nombre", "division", "division_nombre", "activo", "created_at", "updated_at"]


class SubCategorySerializer(serializers.ModelSerializer):
    def validate_category(self, category):
        validar_en_division(self.context["request"], category.division_id, "category", "Esa categoría no es de tu división.")
        if self.instance is not None and category.division_id != self.instance.category.division_id:
            raise serializers.ValidationError("No se puede mover a una categoría de otra división.")
        return category

    category_nombre = serializers.CharField(source="category.nombre", read_only=True)
    efecto_display = serializers.CharField(source="get_efecto_display", read_only=True)
    # Derivada de la categoría (solo lectura).
    division = serializers.IntegerField(source="category.division_id", read_only=True)

    class Meta:
        model = SubCategory
        fields = [
            "id",
            "category",
            "category_nombre",
            "division",
            "nombre",
            "efecto",
            "efecto_display",
            "requiere_proximo_contacto",
            "activo",
            "created_at",
            "updated_at",
        ]


class LeadSerializer(serializers.ModelSerializer):
    campaign_nombre = serializers.CharField(source="campaign.nombre", read_only=True)
    agencia_nombre = serializers.CharField(source="agencia.nombre", read_only=True)
    usuario_asignado_email = serializers.CharField(source="usuario_asignado.email", read_only=True, default=None)
    categoria_actual_nombre = serializers.CharField(source="categoria_actual.nombre", read_only=True, default=None)
    subcategoria_actual_nombre = serializers.CharField(
        source="subcategoria_actual.nombre", read_only=True, default=None
    )
    # División de la campaña: el frontend la usa para ofrecer solo las
    # categorías de tipificación de esa división.
    division = serializers.IntegerField(source="campaign.division_id", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "campaign",
            "campaign_nombre",
            "division",
            "lote_carga",
            "cliente_nombre",
            "telefono",
            "documento_identidad",
            "agencia",
            "agencia_nombre",
            "distrito",
            "usuario_asignado",
            "usuario_asignado_email",
            "fecha_asignacion",
            "estado",
            "categoria_actual",
            "categoria_actual_nombre",
            "subcategoria_actual",
            "subcategoria_actual_nombre",
            "fecha_ultima_gestion",
            "monto_oferta",
            "atributos",
            "atributos_captura",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields  # la escritura pasa por acciones dedicadas (asignar, gestionar en Fase 3)


class AssignmentSerializer(serializers.ModelSerializer):
    usuario_origen_email = serializers.CharField(source="usuario_origen.email", read_only=True, default=None)
    usuario_destino_email = serializers.CharField(source="usuario_destino.email", read_only=True)
    agencia_origen_nombre = serializers.CharField(source="agencia_origen.nombre", read_only=True, default=None)
    agencia_destino_nombre = serializers.CharField(source="agencia_destino.nombre", read_only=True, default=None)
    asignado_por_email = serializers.CharField(source="asignado_por.email", read_only=True)

    class Meta:
        model = Assignment
        fields = [
            "id",
            "lead",
            "usuario_origen",
            "usuario_origen_email",
            "usuario_destino",
            "usuario_destino_email",
            "agencia_origen",
            "agencia_origen_nombre",
            "agencia_destino",
            "agencia_destino_nombre",
            "asignado_por",
            "asignado_por_email",
            "timestamp",
        ]
        read_only_fields = fields


class AsignarLeadInputSerializer(serializers.Serializer):
    usuario_destino = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))


class AsignarMasivoInputSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    usuario_destino = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))


class ManagementLogSerializer(serializers.ModelSerializer):
    usuario_email = serializers.CharField(source="usuario.email", read_only=True)
    category_nombre = serializers.CharField(source="category.nombre", read_only=True)
    subcategory_nombre = serializers.CharField(source="subcategory.nombre", read_only=True, default=None)

    class Meta:
        model = ManagementLog
        fields = [
            "id",
            "lead",
            "usuario",
            "usuario_email",
            "category",
            "category_nombre",
            "subcategory",
            "subcategory_nombre",
            "comentario",
            "fecha_proximo_contacto",
            "timestamp",
        ]
        read_only_fields = fields


class CaptureEntrySerializer(serializers.ModelSerializer):
    usuario_email = serializers.CharField(source="usuario.email", read_only=True)

    class Meta:
        model = CaptureEntry
        fields = ["id", "lead", "usuario", "usuario_email", "datos", "timestamp"]
        read_only_fields = fields


class CrearProspectoInputSerializer(serializers.Serializer):
    """Registro individual de un prospecto (campaign_type.modo_carga=
    INDIVIDUAL) — ver apps.leads.services.crear_prospecto. `agencia` solo es
    obligatoria si quien registra no es EJECUTIVO (ese la toma automática de
    su agencia_principal)."""

    campaign = serializers.PrimaryKeyRelatedField(queryset=Campaign.objects.all())
    agencia = serializers.PrimaryKeyRelatedField(
        queryset=Agencia.objects.filter(activo=True), required=False, allow_null=True
    )
    atributos = serializers.DictField()


class GestionarLeadInputSerializer(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(activo=True))
    subcategory = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.filter(activo=True), required=False, allow_null=True
    )
    comentario = serializers.CharField(allow_blank=False)
    fecha_proximo_contacto = serializers.DateTimeField(required=False, allow_null=True)
    datos_captura = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        # El catálogo es por división: la categoría debe ser de la división de
        # la campaña del lead (`lead` lo pasa la vista en el context).
        lead = self.context.get("lead")
        if lead is not None and attrs["category"].division_id != lead.campaign.division_id:
            raise serializers.ValidationError({"category": "Esta categoría no corresponde a la división de la campaña."})
        subcategory = attrs.get("subcategory")
        if subcategory and subcategory.category_id != attrs["category"].id:
            raise serializers.ValidationError({"subcategory": "No pertenece a la categoría seleccionada."})
        if subcategory and subcategory.requiere_proximo_contacto and not attrs.get("fecha_proximo_contacto"):
            raise serializers.ValidationError(
                {"fecha_proximo_contacto": "Esta subcategoría exige fecha/hora de próximo contacto."}
            )
        return attrs
