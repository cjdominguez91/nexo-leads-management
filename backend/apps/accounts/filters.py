import django_filters as filters

from .models import User


class UserFilter(filters.FilterSet):
    """Un filtro de texto (icontains) por columna, mismo patrón que
    apps.leads.filters.LeadFilter — caja de búsqueda bajo cada encabezado
    en vez de un único cuadro de búsqueda genérico."""

    email = filters.CharFilter(lookup_expr="icontains")
    first_name = filters.CharFilter(lookup_expr="icontains")
    last_name = filters.CharFilter(lookup_expr="icontains")
    codigo_empleado = filters.CharFilter(lookup_expr="icontains")
    role__nombre = filters.CharFilter(field_name="role__nombre", lookup_expr="icontains")
    division__nombre = filters.CharFilter(field_name="division__nombre", lookup_expr="icontains")

    class Meta:
        model = User
        fields = ["role", "division", "is_active", "auth_provider"]
