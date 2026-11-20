from django.contrib import admin

from .models import Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ["lead", "campaign", "estado", "prioridad", "usuario_responsable", "fecha_proximo_contacto"]
    list_filter = ["estado", "prioridad", "campaign"]
    search_fields = ["lead__cliente_nombre"]
