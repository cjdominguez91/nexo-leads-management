from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.models import CatalogModel, TimeStampedModel


class Category(CatalogModel):
    """Catálogo de tipificación. También cubre los antiguos "Motivos-NA" /
    "Motivos-NI" del sistema legado: son Category con sus propias
    SubCategory, no un modelo aparte.

    Pertenece a una División (sus SubCategory la heredan vía `category`): un
    lead solo se puede tipificar con categorías de la división de su campaña."""

    division = models.ForeignKey("accounts.Division", on_delete=models.PROTECT, related_name="categorias")

    class Meta(CatalogModel.Meta):
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"


class SubCategoryEfecto(models.TextChoices):
    """Efecto transversal al tipificar con esta subcategoría: afecta a la
    vez el estado del Lead y el de su Opportunity asociada (se crea si no
    existe). Ej.: bajo la categoría "Contacto Efectivo", "Lo Pensará"/
    "Volver a Llamar" = ABRE_OPORTUNIDAD; "Venta Efectiva" = GANADA;
    "No Aplica"/"No le interesa" = PERDIDA."""

    SIN_EFECTO = "SIN_EFECTO", "Sin efecto"
    ABRE_OPORTUNIDAD = "ABRE_OPORTUNIDAD", "Abre/mantiene oportunidad en progreso"
    GANADA = "GANADA", "Ganada (cierra lead y oportunidad como ganados)"
    PERDIDA = "PERDIDA", "Perdida (cierra lead y oportunidad como perdidos)"


class SubCategory(CatalogModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategorias")
    efecto = models.CharField(max_length=20, choices=SubCategoryEfecto.choices, default=SubCategoryEfecto.SIN_EFECTO)
    requiere_proximo_contacto = models.BooleanField(
        default=False,
        help_text="Si se marca, el formulario de gestión exige fecha/hora de próximo contacto.",
    )

    class Meta(CatalogModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["category", "nombre"], name="unique_category_subcategory_nombre")
        ]
        verbose_name = "Subcategoría"
        verbose_name_plural = "Subcategorías"


class LeadEstado(models.TextChoices):
    NUEVO = "NUEVO", "Nuevo"
    ASIGNADO = "ASIGNADO", "Asignado"
    GESTIONADO = "GESTIONADO", "Gestionado"
    GANADO = "GANADO", "Ganado"
    PERDIDO = "PERDIDO", "Perdido"


class Lead(TimeStampedModel):
    campaign = models.ForeignKey("campaigns.Campaign", on_delete=models.PROTECT, related_name="leads")
    # Nulo para prospectos registrados a mano (campaign_type.modo_carga=
    # INDIVIDUAL) — no vienen de ningún archivo.
    lote_carga = models.ForeignKey(
        "campaigns.LoteCarga", on_delete=models.PROTECT, related_name="leads", null=True, blank=True
    )

    # Únicas 3 columnas fijas de identidad/contacto: las alimenta el campo
    # que el admin marque como es_nombre_cliente/es_telefono_contacto/
    # es_documento_identidad en CampaignFieldDefinition (ver apps.leads.tasks).
    # Quedan como columnas reales (no en atributos JSONB) porque necesitan
    # ser rápidas y universales sin importar cómo se llame el campo en cada
    # campaña. Todo lo demás — incluido correo/dirección — es 100% diseño
    # del admin vía atributos.
    #
    # El dedup usa documento_identidad, NO telefono: el teléfono se recicla
    # entre personas (portabilidad/reasignación de operadoras) y el nombre
    # puede repetirse (homónimos) — el documento es lo único que de verdad
    # identifica a la persona de forma única, así que es el único de los 3
    # verdaderamente obligatorio (ej. bases compradas que solo traen el
    # documento, sin nombre ni teléfono confiables).
    cliente_nombre = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    documento_identidad = models.CharField(max_length=30)

    # Esencial/requerido: siempre viene del archivo origen o del LoteCarga.
    # Determina qué supervisor/jefe ve el lead inicialmente (ver apps.core.scoping).
    agencia = models.ForeignKey("geo.Agencia", on_delete=models.PROTECT, related_name="leads")
    # Opcional: se deriva de agencia.territorio, pero se guarda como columna
    # real (no calculada) para poder filtrar/reportar sin JOIN.
    distrito = models.ForeignKey(
        "geo.Territorio", on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )

    usuario_asignado = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="leads_asignados"
    )
    fecha_asignacion = models.DateTimeField(null=True, blank=True)

    estado = models.CharField(max_length=12, choices=LeadEstado.choices, default=LeadEstado.NUEVO)

    # Denormalizado a propósito (siempre se necesita para reporting/dashboards).
    categoria_actual = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads_categoria_actual"
    )
    subcategoria_actual = models.ForeignKey(
        SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads_subcategoria_actual"
    )
    fecha_ultima_gestion = models.DateTimeField(null=True, blank=True)
    monto_oferta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Solo lo verdaderamente variable por producto (ver CampaignFieldDefinition).
    atributos = models.JSONField(default=dict, blank=True)

    # Snapshot más reciente de los campos origen=CAPTURA_GESTION (campañas de
    # actualización de datos: no vienen del archivo, se llenan al gestionar).
    # Separado de `atributos` a propósito — no mezclar "lo que trajo la
    # base" con "lo que se levantó en la llamada". El historial completo de
    # cada captura vive en CaptureEntry (append-only, como ManagementLog).
    atributos_captura = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [GinIndex(fields=["atributos"], name="lead_atributos_gin")]
        constraints = [
            # Respaldo a nivel de base de datos del dedup de apps.leads.tasks
            # (que además da el mensaje de error amigable) — excluye vacíos
            # para no romper leads legacy cargados antes de este campo.
            models.UniqueConstraint(
                fields=["campaign", "documento_identidad"],
                condition=models.Q(documento_identidad__gt=""),
                name="unique_campaign_documento_identidad",
            )
        ]

    def __str__(self):
        return f"{self.cliente_nombre} ({self.telefono})"


class Assignment(models.Model):
    """Historial de asignaciones, append-only. Cada fila que cambia de
    agencia debe ir junto con la actualización de Lead.agencia en la misma
    transacción (ver apps.leads.services.reasignar_lead)."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="historial_asignaciones")
    usuario_origen = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="asignaciones_como_origen"
    )
    usuario_destino = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="asignaciones_como_destino"
    )
    agencia_origen = models.ForeignKey(
        "geo.Agencia", on_delete=models.SET_NULL, null=True, blank=True, related_name="asignaciones_como_origen"
    )
    agencia_destino = models.ForeignKey(
        "geo.Agencia", on_delete=models.SET_NULL, null=True, blank=True, related_name="asignaciones_como_destino"
    )
    asignado_por = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="asignaciones_realizadas")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Asignación"
        verbose_name_plural = "Asignaciones"

    def __str__(self):
        return f"Lead #{self.lead_id} -> {self.usuario_destino}"


class ManagementLog(models.Model):
    """Tipificación/gestión de un lead. Append-only — nunca se edita ni
    borra, es la línea de evolución del lead (ver apps.leads.services.tipificar_lead)."""

    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="gestiones")
    usuario = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="gestiones_realizadas")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="gestiones")
    subcategory = models.ForeignKey(
        SubCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="gestiones"
    )
    comentario = models.TextField()
    fecha_proximo_contacto = models.DateTimeField(
        null=True, blank=True, help_text="Solo si subcategory.requiere_proximo_contacto."
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Gestión"
        verbose_name_plural = "Gestiones"

    def __str__(self):
        return f"Lead #{self.lead_id} tipificado {self.category} por {self.usuario}"


class CaptureEntry(models.Model):
    """Historial append-only de capturas de datos (campos origen=
    CAPTURA_GESTION) — se crea junto con un ManagementLog cuando el
    formulario de captura no llega vacío (ver apps.leads.services.tipificar_lead).
    Mismo espíritu que ManagementLog: nunca se edita ni se borra."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="capturas")
    usuario = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="capturas_realizadas")
    datos = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Captura de datos"
        verbose_name_plural = "Capturas de datos"

    def __str__(self):
        return f"Lead #{self.lead_id} captura por {self.usuario}"
