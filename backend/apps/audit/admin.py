from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "usuario", "accion", "modelo_afectado", "id_afectado", "ip_address"]
    list_filter = ["accion", "modelo_afectado"]
    search_fields = ["usuario__email", "id_afectado"]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
