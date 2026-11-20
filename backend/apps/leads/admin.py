from django.contrib import admin

from .models import Assignment, Category, Lead, ManagementLog, SubCategory


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo"]
    inlines = [SubCategoryInline]


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ["nombre", "category", "efecto", "requiere_proximo_contacto", "activo"]
    list_filter = ["category", "efecto", "activo"]


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 0
    readonly_fields = [f.name for f in Assignment._meta.fields]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ManagementLogInline(admin.TabularInline):
    model = ManagementLog
    extra = 0
    readonly_fields = [f.name for f in ManagementLog._meta.fields]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["cliente_nombre", "telefono", "campaign", "agencia", "usuario_asignado", "estado"]
    list_filter = ["estado", "campaign", "agencia"]
    search_fields = ["cliente_nombre", "telefono", "correo"]
    inlines = [AssignmentInline, ManagementLogInline]
