"""Punto único para crear una Notification y empujarla por WebSocket a la
vez. Se llama explícitamente desde la capa de servicios (asignar individual,
asignar masivo agrupado, reclamo por inactividad de crear_prospecto, y
crear/cerrar una Opportunity) — nunca desde dentro de un loop por registro,
para no generar una notificación por cada lead cuando se asigna en bloque.

Deliberadamente solo notifica a quien RECIBE el/los registro(s) o es
responsable de la oportunidad — a pedido explícito del usuario, no se
notifica a quien los pierde, ni a quien generó el evento con su propia
acción (ver el chequeo en apps.leads.services._tocar_oportunidad).
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification, NotificationTipo
from .serializers import NotificationSerializer


def _emit(*, usuario_id: int, tipo: str, payload: dict) -> Notification:
    notification = Notification.objects.create(usuario_id=usuario_id, tipo=tipo, payload=payload)
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f"user_{usuario_id}",
            {"type": "notify_event", "data": NotificationSerializer(notification).data},
        )
    return notification


def notificar_asignacion(*, usuario_destino_id: int, campaign, cantidad: int, motivo: str):
    """`campaign` es la Campaign (o Prospección) a la que pertenecen los
    registros asignados. `cantidad` es cuántos registros le tocaron a este
    usuario en este evento (1 para asignación individual o reclamo de
    prospecto; N para una asignación masiva)."""

    payload = {
        "campaign_id": campaign.id,
        "campaign_nombre": campaign.nombre,
        "campaign_modo_carga": campaign.campaign_type.modo_carga,
        "cantidad": cantidad,
        "motivo": motivo,
    }
    _emit(usuario_id=usuario_destino_id, tipo=NotificationTipo.ASIGNACION_RECIBIDA, payload=payload)


def notificar_oportunidad(*, usuario_responsable_id: int, opportunity, tipo: str):
    """`tipo` es OPORTUNIDAD_CREADA (se abrió una oportunidad nueva) u
    OPORTUNIDAD_CERRADA (pasó a GANADA/PERDIDA) — ver el único punto que
    dispara esto, apps.leads.services._tocar_oportunidad."""

    lead = opportunity.lead
    payload = {
        "lead_id": lead.id,
        "cliente_nombre": lead.cliente_nombre or lead.documento_identidad,
        "campaign_id": opportunity.campaign_id,
        "campaign_nombre": opportunity.campaign.nombre,
        "opportunity_id": opportunity.id,
        "estado": opportunity.estado,
    }
    _emit(usuario_id=usuario_responsable_id, tipo=tipo, payload=payload)
