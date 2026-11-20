from django.db import models

from apps.core.models import TimeStampedModel


class NotificationTipo(models.TextChoices):
    """Eventos de asignación/reasignación (ver
    apps.notifications.services.notificar_asignacion) y de oportunidades
    (ver notificar_oportunidad, disparado desde apps.leads.services.
    _tocar_oportunidad).

    Deliberadamente NO existe un tipo para "te quitaron un registro" — a
    pedido explícito del usuario, solo se notifica a quien recibe, nunca a
    quien lo pierde. Tampoco existen tipos para cambio de prioridad de una
    oportunidad (ruido, sin urgencia) ni para "próximo contacto por vencer"
    (eso es un recordatorio programado, no un evento — candidato a una tarea
    de Celery Beat aparte si se necesita)."""

    ASIGNACION_RECIBIDA = "ASIGNACION_RECIBIDA", "Te asignaron registro(s)"
    OPORTUNIDAD_CREADA = "OPORTUNIDAD_CREADA", "Se creó una oportunidad para tu lead"
    OPORTUNIDAD_CERRADA = "OPORTUNIDAD_CERRADA", "Tu oportunidad se cerró"


class Notification(TimeStampedModel):
    """In-app, vía WebSocket. `payload` trae lo necesario para el toast y
    para que el frontend actualice la lista en vivo sin recargar (lead_id,
    campaign_id, cliente_nombre, motivo, etc.) — se diseña desde el
    principio para poder sumar email como canal adicional después sin
    rehacer el modelo (bastaría con un EmailNotifier que lea estas mismas
    filas)."""

    usuario = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="notificaciones")
    tipo = models.CharField(max_length=30, choices=NotificationTipo.choices)
    payload = models.JSONField(default=dict, blank=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.tipo} -> {self.usuario}"
