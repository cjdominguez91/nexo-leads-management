from django.db import models

from apps.core.models import TimeStampedModel


class OpportunityEstado(models.TextChoices):
    EN_PROGRESO = "EN_PROGRESO", "En progreso"
    GANADA = "GANADA", "Ganada"
    PERDIDA = "PERDIDA", "Perdida"


class OpportunityPrioridad(models.TextChoices):
    ALTA = "ALTA", "Alta"
    MEDIA = "MEDIA", "Media"
    BAJA = "BAJA", "Baja"


class Opportunity(TimeStampedModel):
    """Nace siempre de tipificar un lead con una SubCategory cuyo `efecto`
    no sea SIN_EFECTO (ver apps.leads.services.tipificar_lead) — no existe
    creación manual/independiente. No duplica datos del producto/oferta:
    esos ya viven en Lead.atributos (esquema dinámico por CampaignType), así
    que esta tabla es solo el "marcador" de seguimiento comercial: quién es
    responsable, prioridad, estado y próximo contacto."""

    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="oportunidades")
    campaign = models.ForeignKey("campaigns.Campaign", on_delete=models.PROTECT, related_name="oportunidades")
    usuario_responsable = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="oportunidades")
    prioridad = models.CharField(
        max_length=10, choices=OpportunityPrioridad.choices, default=OpportunityPrioridad.MEDIA
    )
    estado = models.CharField(
        max_length=12, choices=OpportunityEstado.choices, default=OpportunityEstado.EN_PROGRESO
    )
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    fecha_proximo_contacto = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Oportunidad"
        verbose_name_plural = "Oportunidades"

    def __str__(self):
        return f"Oportunidad #{self.pk} · lead #{self.lead_id}"
