from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Division, Role, User, UserAgencia, UserTerritorio


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["nombre", "nivel_jerarquico", "descripcion"]


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "activo"]
    search_fields = ["nombre", "codigo"]
    list_filter = ["activo"]


class UserAgenciaInline(admin.TabularInline):
    model = UserAgencia
    extra = 0
    fk_name = "usuario"


class UserTerritorioInline(admin.TabularInline):
    model = UserTerritorio
    extra = 0
    fk_name = "usuario"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "role", "agencia_principal", "auth_provider", "is_active"]
    list_filter = ["role", "auth_provider", "is_active", "division"]
    search_fields = ["email", "first_name", "last_name"]
    inlines = [UserAgenciaInline, UserTerritorioInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "avatar_url")}),
        (
            "Rol y alcance",
            {"fields": ("role", "division", "agencia_principal", "auth_provider")},
        ),
        (
            "Permisos",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role", "is_staff", "is_superuser"),
            },
        ),
    )
