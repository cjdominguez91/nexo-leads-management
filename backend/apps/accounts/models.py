from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import CatalogModel

from .constants import RoleNames


class Division(CatalogModel):
    """Unidad de negocio (ej. "Red de Agencias", "Banca Empresas"). Filtra,
    junto al scope territorial, qué campañas/leads puede ver un usuario."""

    codigo = models.CharField(max_length=20, unique=True)

    class Meta(CatalogModel.Meta):
        verbose_name = "División"
        verbose_name_plural = "Divisiones"


class Role(models.Model):
    """Catálogo fijo (seed vía migración) de los 6 roles del sistema. No es
    un CRUD libre: agregar un rol nuevo requiere extender apps.core.scoping."""

    nombre = models.CharField(max_length=20, unique=True, choices=RoleNames.choices)
    nivel_jerarquico = models.PositiveSmallIntegerField(
        help_text="Menor número = más alto en la jerarquía (ADMIN=1)."
    )
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["nivel_jerarquico"]
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.get_nombre_display()


class AuthProvider(models.TextChoices):
    GOOGLE = "google", "Google"
    LOCAL = "local", "Local"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    # Nulo a nivel de BD a propósito: usuarios pre-existentes o creados por
    # flujos que no pasan por el alta de ADMIN (ej. autoprovisión por Google
    # SSO) no deben romper. Lo "obligatorio" se exige en UserCreateSerializer,
    # que es el único punto de alta manual de empleados.
    codigo_empleado = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        help_text="Código interno de empleado de la organización.",
    )

    role = models.ForeignKey(
        Role, on_delete=models.PROTECT, related_name="usuarios", null=True, blank=True
    )
    division = models.ForeignKey(
        Division, on_delete=models.SET_NULL, related_name="usuarios", null=True, blank=True
    )
    agencia_principal = models.ForeignKey(
        "geo.Agencia",
        on_delete=models.SET_NULL,
        related_name="ejecutivos",
        null=True,
        blank=True,
        help_text="Agencia única, aplica solo a EJECUTIVO. JEFE/SUBJEFE/SUPERVISOR "
        "usan UserAgencia/UserTerritorio (pueden cubrir varias).",
    )
    auth_provider = models.CharField(
        max_length=10, choices=AuthProvider.choices, default=AuthProvider.LOCAL
    )
    avatar_url = models.URLField(blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email


class UserAgencia(models.Model):
    """M2M explícita usuario↔agencia (JEFE/SUBJEFE pueden cubrir varias)."""

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="agencias_asignadas")
    agencia = models.ForeignKey(
        "geo.Agencia", on_delete=models.CASCADE, related_name="asignaciones_usuario"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Asignación usuario-agencia"
        verbose_name_plural = "Asignaciones usuario-agencia"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "agencia"],
                condition=models.Q(activo=True),
                name="unique_usuario_agencia_activa",
            )
        ]

    def __str__(self):
        estado = "activo" if self.activo else "inactivo"
        return f"{self.usuario} -> {self.agencia} ({estado})"


class UserTerritorio(models.Model):
    """M2M explícita usuario↔territorio (SUPERVISOR puede cubrir varios distritos)."""

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="territorios_asignados")
    territorio = models.ForeignKey(
        "geo.Territorio", on_delete=models.CASCADE, related_name="asignaciones_usuario"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Asignación usuario-territorio"
        verbose_name_plural = "Asignaciones usuario-territorio"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "territorio"],
                condition=models.Q(activo=True),
                name="unique_usuario_territorio_activo",
            )
        ]

    def __str__(self):
        estado = "activo" if self.activo else "inactivo"
        return f"{self.usuario} -> {self.territorio} ({estado})"
