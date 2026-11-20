from django.contrib import admin

from .models import Campaign, CampaignFieldDefinition, CampaignType, LoteCarga


class CampaignFieldDefinitionInline(admin.TabularInline):
    model = CampaignFieldDefinition
    extra = 0


@admin.register(CampaignType)
class CampaignTypeAdmin(admin.ModelAdmin):
    list_display = ["nombre", "categoria"]
    list_filter = ["categoria"]
    inlines = [CampaignFieldDefinitionInline]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["nombre", "campaign_type", "division", "estado", "fecha_inicio", "fecha_fin"]
    list_filter = ["estado", "campaign_type", "division"]
    search_fields = ["nombre"]


@admin.register(LoteCarga)
class LoteCargaAdmin(admin.ModelAdmin):
    list_display = ["nombre_archivo", "campaign", "usuario_carga", "estado", "cantidad_registros", "created_at"]
    list_filter = ["estado", "campaign"]
    readonly_fields = ["cantidad_registros", "errores", "estado"]
