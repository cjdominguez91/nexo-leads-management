from datetime import datetime, timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.campaigns.models import CampaignEstado
from apps.leads.models import LeadEstado, ManagementLog
from apps.leads.services import leads_visibles_para
from apps.opportunities.models import Opportunity, OpportunityEstado

DIAS_ALERTA_SIN_GESTIONAR = 7


def _leads_filtrados(request, *, fecha_desde=None, fecha_hasta=None):
    """Punto único de filtros del dashboard — mismos query params en todas
    las vistas, siempre partiendo de leads_visibles_para (el scope
    territorial es un techo, nunca se puede ampliar vía filtro).

    `fecha_desde`/`fecha_hasta` explícitos (usados por `_variacion` para
    recalcular el período anterior) pisan los que vengan en query params."""

    qs = leads_visibles_para(request.user)
    params = request.query_params
    if params.get("campaign"):
        qs = qs.filter(campaign_id=params["campaign"])
    if params.get("agencia"):
        qs = qs.filter(agencia_id=params["agencia"])
    if params.get("distrito"):
        qs = qs.filter(distrito_id=params["distrito"])
    if params.get("usuario_asignado"):
        qs = qs.filter(usuario_asignado_id=params["usuario_asignado"])

    desde = fecha_desde if fecha_desde is not None else params.get("fecha_desde")
    hasta = fecha_hasta if fecha_hasta is not None else params.get("fecha_hasta")
    if desde:
        qs = qs.filter(created_at__date__gte=desde)
    if hasta:
        qs = qs.filter(created_at__date__lte=hasta)
    return qs


def _tiempo_promedio_primera_gestion_horas(qs):
    """Promedio de horas entre fecha_asignacion y el primer ManagementLog,
    solo sobre leads que sí llegaron a gestionarse al menos una vez."""

    primera_gestion = ManagementLog.objects.filter(lead=OuterRef("pk")).order_by("timestamp").values("timestamp")[:1]
    con_gestion = (
        qs.filter(fecha_asignacion__isnull=False)
        .annotate(primera_gestion=Subquery(primera_gestion))
        .filter(primera_gestion__isnull=False)
        .annotate(demora=ExpressionWrapper(F("primera_gestion") - F("fecha_asignacion"), output_field=DurationField()))
    )
    promedio = con_gestion.aggregate(promedio=Avg("demora"))["promedio"]
    return round(promedio.total_seconds() / 3600, 1) if promedio else None


def _variacion(request):
    """Compara tasa_contacto/tasa_efectividad del período actual (definido
    por `fecha_desde` en query params) contra un período anterior de igual
    duración, inmediatamente antes. Sin `fecha_desde` (vista "todo el
    histórico") no hay período que comparar, así que devuelve None —
    "variación vs período anterior" no tiene sentido sin un período."""

    fecha_desde_str = request.query_params.get("fecha_desde")
    if not fecha_desde_str:
        return None
    fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d").date()
    dias = (timezone.localdate() - fecha_desde).days
    if dias <= 0:
        return None

    qs_anterior = _leads_filtrados(request, fecha_desde=fecha_desde - timedelta(days=dias), fecha_hasta=fecha_desde - timedelta(days=1))
    total_anterior = qs_anterior.count()
    if not total_anterior:
        return None

    contactados_anterior = qs_anterior.filter(fecha_ultima_gestion__isnull=False).count()
    ganados_anterior = qs_anterior.filter(estado=LeadEstado.GANADO).count()
    return {
        "tasa_contacto": round(contactados_anterior / total_anterior, 4),
        "tasa_efectividad": round(ganados_anterior / total_anterior, 4),
    }


class ResumenView(APIView):
    """Vista 360: estado actual de los leads dentro del alcance del usuario
    (KPIs + desglose por estado/categoría/subcategoría)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _leads_filtrados(request)
        total = qs.count()

        por_estado = {row["estado"]: row["cantidad"] for row in qs.values("estado").annotate(cantidad=Count("id"))}
        for estado in LeadEstado.values:
            por_estado.setdefault(estado, 0)

        por_categoria = (
            qs.filter(categoria_actual__isnull=False)
            .values("categoria_actual__nombre")
            .annotate(cantidad=Count("id"))
            .order_by("-cantidad")[:10]
        )
        por_subcategoria = (
            qs.filter(subcategoria_actual__isnull=False)
            .values("subcategoria_actual__nombre")
            .annotate(cantidad=Count("id"))
            .order_by("-cantidad")[:10]
        )

        contactados = qs.filter(fecha_ultima_gestion__isnull=False).count()
        ganados = por_estado.get(LeadEstado.GANADO, 0)

        # "Sin gestionar hace más de N días": abiertos (no GANADO/PERDIDO)
        # cuya última actividad (gestión, o asignación si nunca se gestionó,
        # o alta si tampoco se asignó) ya pasó el umbral de alerta.
        referencia = Coalesce("fecha_ultima_gestion", "fecha_asignacion", "created_at")
        umbral = timezone.now() - timedelta(days=DIAS_ALERTA_SIN_GESTIONAR)
        sin_gestionar = (
            qs.filter(estado__in=[LeadEstado.NUEVO, LeadEstado.ASIGNADO, LeadEstado.GESTIONADO])
            .annotate(referencia=referencia)
            .filter(referencia__lt=umbral)
            .count()
        )

        hoy = timezone.localdate()
        campanas_activas = (
            qs.filter(
                Q(campaign__estado=CampaignEstado.ACTIVA)
                & (Q(campaign__fecha_fin__isnull=True) | Q(campaign__fecha_fin__gte=hoy))
            )
            .values("campaign_id")
            .distinct()
            .count()
        )
        leads_activos = qs.exclude(estado__in=[LeadEstado.GANADO, LeadEstado.PERDIDO]).count()
        sin_asignar = qs.filter(usuario_asignado__isnull=True).count()

        return Response(
            {
                "total": total,
                "por_estado": por_estado,
                "por_categoria": [
                    {"categoria": row["categoria_actual__nombre"], "cantidad": row["cantidad"]} for row in por_categoria
                ],
                "por_subcategoria": [
                    {"subcategoria": row["subcategoria_actual__nombre"], "cantidad": row["cantidad"]}
                    for row in por_subcategoria
                ],
                "tasa_contacto": round(contactados / total, 4) if total else 0,
                "tasa_efectividad": round(ganados / total, 4) if total else 0,
                "tasa_conversion": round(ganados / contactados, 4) if contactados else 0,
                "sin_gestionar_hace_mas_de_7_dias": sin_gestionar,
                "sin_asignar": sin_asignar,
                "campanas_activas": campanas_activas,
                "leads_activos": leads_activos,
                "tiempo_promedio_primera_gestion_horas": _tiempo_promedio_primera_gestion_horas(qs),
                "variacion": _variacion(request),
            }
        )


class TendenciaView(APIView):
    """Serie de tiempo: gestiones registradas y oportunidades ganadas por
    día, con el mismo alcance/filtros que el resto del dashboard.

    Es la única vista del dashboard con recorte temporal propio: los KPIs
    miden la campaña completa, pero aquí sí interesa ver el ritmo en el
    tiempo. `dias` ausente o 0 = todo el histórico; `dias=N` = últimos N."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            dias = max(int(request.query_params.get("dias", 0)), 0)
        except ValueError:
            return Response({"detail": "dias debe ser un entero >= 0"}, status=400)

        lead_ids = _leads_filtrados(request).values_list("id", flat=True)
        gestiones_qs = ManagementLog.objects.filter(lead_id__in=lead_ids)
        ganadas_qs = Opportunity.objects.filter(lead_id__in=lead_ids, estado=OpportunityEstado.GANADA)
        if dias:
            desde = timezone.now() - timedelta(days=dias)
            gestiones_qs = gestiones_qs.filter(timestamp__gte=desde)
            ganadas_qs = ganadas_qs.filter(fecha_cierre__gte=desde)

        gestiones = (
            gestiones_qs.annotate(fecha=TruncDate("timestamp"))
            .values("fecha")
            .annotate(cantidad=Count("id"))
            .order_by("fecha")
        )
        ganadas = (
            ganadas_qs.annotate(fecha=TruncDate("fecha_cierre"))
            .values("fecha")
            .annotate(cantidad=Count("id"))
            .order_by("fecha")
        )

        return Response(
            {
                "gestiones_por_dia": [{"fecha": row["fecha"], "cantidad": row["cantidad"]} for row in gestiones],
                "ganadas_por_dia": [{"fecha": row["fecha"], "cantidad": row["cantidad"]} for row in ganadas],
            }
        )


# Dimensión de agrupación -> (campo id, campo nombre) sobre Lead.
AGRUPACIONES = {
    "campaign": ("campaign_id", "campaign__nombre"),
    "distrito": ("distrito_id", "distrito__nombre"),
    "agencia": ("agencia_id", "agencia__nombre"),
    "usuario_asignado": ("usuario_asignado_id", "usuario_asignado__email"),
}


class EfectividadView(APIView):
    """Efectividad agregada por la dimensión que pida `agrupar_por`
    (campaign/distrito/agencia/usuario_asignado) — una sola vista genérica
    en vez de un endpoint por dimensión, ya que la agregación es idéntica y
    solo cambia el GROUP BY. Cubre "distribución por campaña" (Admin/
    Gerente), "efectividad por distrito/agencia/ejecutivo" y, ordenando/
    recortando en el frontend, el ranking top/bottom 5."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        agrupar_por = request.query_params.get("agrupar_por", "campaign")
        if agrupar_por not in AGRUPACIONES:
            return Response(
                {"detail": f"agrupar_por debe ser uno de: {', '.join(AGRUPACIONES)}"}, status=400
            )
        id_field, nombre_field = AGRUPACIONES[agrupar_por]

        qs = _leads_filtrados(request)
        rows = (
            qs.filter(**{f"{id_field}__isnull": False})
            .values(id_field, nombre_field)
            .annotate(
                total=Count("id"),
                contactados=Count("id", filter=Q(fecha_ultima_gestion__isnull=False)),
                ganados=Count("id", filter=Q(estado=LeadEstado.GANADO)),
                perdidos=Count("id", filter=Q(estado=LeadEstado.PERDIDO)),
            )
            .order_by("-total")
        )

        data = []
        for row in rows:
            total = row["total"]
            data.append(
                {
                    "id": row[id_field],
                    "nombre": row[nombre_field],
                    "total": total,
                    "contactados": row["contactados"],
                    "tasa_contacto": round(row["contactados"] / total, 4) if total else 0,
                    "ganados": row["ganados"],
                    "tasa_efectividad": round(row["ganados"] / total, 4) if total else 0,
                    "perdidos": row["perdidos"],
                }
            )
        return Response(data)
