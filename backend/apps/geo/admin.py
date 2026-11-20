from django.contrib import admin

from .models import Agencia, Territorio


@admin.register(Territorio)
class TerritorioAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "activo"]
    search_fields = ["nombre", "codigo"]
    list_filter = ["activo"]


@admin.register(Agencia)
class AgenciaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "territorio", "activo"]
    search_fields = ["nombre", "codigo"]
    list_filter = ["activo", "territorio"]
