import django_filters as filters

from .models import Lead


class LeadFilter(filters.FilterSet):
    """Un filtro de texto (icontains) por columna — como el DataTable del
    sistema original, una caja de búsqueda bajo cada encabezado en vez de un
    único cuadro de búsqueda genérico. Los campos dinámicos (atributos
    JSONB) no se declaran acá porque varían por CampaignType; se resuelven
    aparte en LeadViewSet.get_queryset a partir de query params `attr__<key>`."""

    documento_identidad = filters.CharFilter(lookup_expr="icontains")
    cliente_nombre = filters.CharFilter(lookup_expr="icontains")
    telefono = filters.CharFilter(lookup_expr="icontains")
    estado = filters.CharFilter(lookup_expr="icontains")
    agencia__nombre = filters.CharFilter(field_name="agencia__nombre", lookup_expr="icontains")
    usuario_asignado__email = filters.CharFilter(field_name="usuario_asignado__email", lookup_expr="icontains")
    categoria_actual__nombre = filters.CharFilter(field_name="categoria_actual__nombre", lookup_expr="icontains")
    subcategoria_actual__nombre = filters.CharFilter(
        field_name="subcategoria_actual__nombre", lookup_expr="icontains"
    )

    class Meta:
        model = Lead
        fields = ["campaign", "agencia", "usuario_asignado"]
