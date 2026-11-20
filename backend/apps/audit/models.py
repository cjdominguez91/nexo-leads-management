from django.db import models


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Creación"
    UPDATE = "UPDATE", "Actualización"
    DELETE = "DELETE", "Baja"
    LOGIN = "LOGIN", "Inicio de sesión"


class AuditLog(models.Model):
    """Trazabilidad genérica, append-only. Se escribe vía signals (ver
    apps.audit.signals) o explícitamente desde vistas para acciones de
    dominio que no son un simple CRUD (ej. asignación de leads, fase 2)."""

    usuario = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acciones_auditadas",
    )
    accion = models.CharField(max_length=50, choices=AuditAction.choices)
    modelo_afectado = models.CharField(max_length=100)
    id_afectado = models.CharField(max_length=64)
    datos_antes = models.JSONField(null=True, blank=True)
    datos_despues = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["modelo_afectado", "id_afectado"]),
            models.Index(fields=["usuario", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.accion} {self.modelo_afectado}#{self.id_afectado} por {self.usuario_id}"
