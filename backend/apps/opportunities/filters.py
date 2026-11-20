import django_filters as filters

from .models import Opportunity


class OpportunityFilter(filters.FilterSet):
    """Un filtro de texto (icontains) por columna, mismo patrón que
    apps.leads.filters.LeadFilter — todos atraviesan relaciones (lead/
    campaign), por eso van declarados explícitamente en vez de listados
    en Meta.fields."""

    documento_identidad = filters.CharFilter(field_name="lead__documento_identidad", lookup_expr="icontains")
    cliente_nombre = filters.CharFilter(field_name="lead__cliente_nombre", lookup_expr="icontains")
    campaign_nombre = filters.CharFilter(field_name="campaign__nombre", lookup_expr="icontains")
    categoria_actual_nombre = filters.CharFilter(
        field_name="lead__categoria_actual__nombre", lookup_expr="icontains"
    )
    subcategoria_actual_nombre = filters.CharFilter(
        field_name="lead__subcategoria_actual__nombre", lookup_expr="icontains"
    )
    estado = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Opportunity
        fields = ["prioridad", "lead", "usuario_responsable"]
