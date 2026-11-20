from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.core.scoping import es_global
from apps.geo.models import Agencia, Territorio

from .constants import ROLES_GESTIONABLES_POR_ADMIN_DIVISION, RoleNames
from .models import Division, Role, User, UserAgencia, UserTerritorio


def validar_alta_o_edicion_usuario(serializer, attrs):
    """Reglas comunes a crear y editar usuarios.

    Para un ADMIN_DIVISION (no global):
    - La división del usuario es siempre la suya (lo que mande se ignora).
    - Solo puede asignar roles de ROLES_GESTIONABLES_POR_ADMIN_DIVISION:
      nunca ADMIN ni ADMIN_DIVISION (evita auto-escalarse o crear pares).
    Para todos:
    - Todo rol que no sea ADMIN necesita división (sin división no ve nada).
    - La agencia principal debe ser de la división del usuario."""

    request = serializer.context["request"]
    actor = request.user
    instance = serializer.instance

    role = attrs.get("role", getattr(instance, "role", None))
    if not es_global(actor):
        attrs["division"] = actor.division
        if role is not None and role.nombre not in ROLES_GESTIONABLES_POR_ADMIN_DIVISION:
            raise serializers.ValidationError({"role": "No puedes asignar ese rol."})

    division = attrs.get("division", getattr(instance, "division", None))
    if role is not None and role.nombre != RoleNames.ADMIN and division is None:
        raise serializers.ValidationError({"division": "Obligatoria para este rol."})

    agencia = attrs.get("agencia_principal", getattr(instance, "agencia_principal", None))
    if agencia is not None and (division is None or agencia.territorio.division_id != division.id):
        raise serializers.ValidationError({"agencia_principal": "La agencia no pertenece a la división del usuario."})
    return attrs


class RoleSerializer(serializers.ModelSerializer):
    nombre_display = serializers.CharField(source="get_nombre_display", read_only=True)

    class Meta:
        model = Role
        fields = ["id", "nombre", "nombre_display", "nivel_jerarquico", "descripcion"]


class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = ["id", "nombre", "codigo", "activo", "created_at", "updated_at"]


class UserAgenciaSerializer(serializers.ModelSerializer):
    agencia_nombre = serializers.CharField(source="agencia.nombre", read_only=True)

    class Meta:
        model = UserAgencia
        fields = ["id", "agencia", "agencia_nombre", "fecha_asignacion", "activo"]
        read_only_fields = ["fecha_asignacion"]


class UserTerritorioSerializer(serializers.ModelSerializer):
    territorio_nombre = serializers.CharField(source="territorio.nombre", read_only=True)

    class Meta:
        model = UserTerritorio
        fields = ["id", "territorio", "territorio_nombre", "fecha_asignacion", "activo"]
        read_only_fields = ["fecha_asignacion"]


class UserSerializer(serializers.ModelSerializer):
    """Lectura/edición de usuarios existentes. La creación usa
    UserCreateSerializer porque maneja contraseña + provider de forma distinta."""

    role_nombre = serializers.CharField(source="role.nombre", read_only=True, default=None)
    agencia_principal_nombre = serializers.CharField(
        source="agencia_principal.nombre", read_only=True, default=None
    )
    division_nombre = serializers.CharField(source="division.nombre", read_only=True, default=None)
    agencias = UserAgenciaSerializer(source="agencias_asignadas", many=True, read_only=True)
    territorios = UserTerritorioSerializer(source="territorios_asignados", many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "codigo_empleado",
            "role",
            "role_nombre",
            "division",
            "division_nombre",
            "agencia_principal",
            "agencia_principal_nombre",
            "auth_provider",
            "avatar_url",
            "is_active",
            "is_superuser",
            "date_joined",
            "last_login",
            "agencias",
            "territorios",
        ]
        read_only_fields = ["date_joined", "last_login", "auth_provider", "is_superuser"]

    def validate(self, attrs):
        return validar_alta_o_edicion_usuario(self, super().validate(attrs))


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # Obligatorio solo en este serializer (el de alta manual desde el panel
    # de ADMIN) — el campo en el modelo es nullable para no romper usuarios
    # existentes ni la autoprovisión por Google SSO (ver models.py).
    codigo_empleado = serializers.CharField(required=True, max_length=30)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "codigo_empleado",
            "role",
            "division",
            "agencia_principal",
            "password",
            "is_active",
        ]

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def validate(self, attrs):
        return validar_alta_o_edicion_usuario(self, super().validate(attrs))

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user


class AgenciaAsignacionInputSerializer(serializers.Serializer):
    agencia = serializers.PrimaryKeyRelatedField(queryset=Agencia.objects.filter(activo=True))


class TerritorioAsignacionInputSerializer(serializers.Serializer):
    territorio = serializers.PrimaryKeyRelatedField(queryset=Territorio.objects.filter(activo=True))
