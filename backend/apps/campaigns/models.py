from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class CampaignCategoria(models.TextChoices):
    VENTAS = "VENTAS", "Ventas"
    COBROS = "COBROS", "Cobros"


class CampaignModoCarga(models.TextChoices):
    """Cómo entran los registros a una campaña de este tipo. MASIVA es el
    caso normal (archivo CSV/XLSX vía LoteCarga). INDIVIDUAL es para
    "Prospección": no hay archivo, cada registro lo crea un usuario a mano,
    uno por uno (ver apps.leads.services.crear_prospecto). El frontend usa
    esto para decidir si una Campaign se muestra en "Campañas" o en
    "Prospección" — es la misma tabla, solo cambia cómo se llenan los datos."""

    MASIVA = "MASIVA", "Carga masiva (archivo)"
    INDIVIDUAL = "INDIVIDUAL", "Registro individual (uno por uno)"


class CampaignType(TimeStampedModel):
    """"Contenedor"/plantilla de campaña (ej. "Créditos Personales"). Define,
    vía CampaignFieldDefinition, el esquema dinámico de sus campañas."""

    nombre = models.CharField(max_length=150, unique=True)
    categoria = models.CharField(max_length=20, choices=CampaignCategoria.choices)
    modo_carga = models.CharField(
        max_length=20, choices=CampaignModoCarga.choices, default=CampaignModoCarga.MASIVA
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Tipo de campaña"
        verbose_name_plural = "Tipos de campaña"

    def __str__(self):
        return self.nombre


class CampaignEstado(models.TextChoices):
    ACTIVA = "ACTIVA", "Activa"
    CERRADA = "CERRADA", "Cerrada"


class Campaign(TimeStampedModel):
    nombre = models.CharField(max_length=150)
    campaign_type = models.ForeignKey(CampaignType, on_delete=models.PROTECT, related_name="campaigns")
    division = models.ForeignKey("accounts.Division", on_delete=models.PROTECT, related_name="campaigns")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=CampaignEstado.choices, default=CampaignEstado.ACTIVA)
    producto_default = models.CharField(
        max_length=150, blank=True, help_text="Producto por defecto; cada LoteCarga puede sobreescribirlo."
    )

    # Vacío = sin restricción (abierta a toda agencia/distrito dentro del
    # alcance normal por división+territorio de cada rol). Si se define,
    # solo esas agencias/distritos pueden ver y gestionar la campaña —
    # se combina con el scoping normal, no lo reemplaza (ver
    # apps.core.scoping.campanas_visibles_para).
    agencias_habilitadas = models.ManyToManyField(
        "geo.Agencia", blank=True, related_name="campaigns_habilitadas"
    )
    distritos_habilitados = models.ManyToManyField(
        "geo.Territorio", blank=True, related_name="campaigns_habilitadas"
    )

    class Meta:
        ordering = ["-fecha_inicio"]

    def __str__(self):
        return self.nombre

    @property
    def esta_cerrada(self) -> bool:
        """Cerrada explícitamente por ADMIN, o vencida por fecha_fin. Se
        calcula al vuelo (no hay job que voltee `estado` automáticamente)
        para que siempre sea exacta sin depender de un cron."""
        if self.estado == CampaignEstado.CERRADA:
            return True
        return bool(self.fecha_fin and self.fecha_fin < timezone.localdate())


class CampaignSection(TimeStampedModel):
    """Agrupa campos de un CampaignType para renderizarlos juntos en el
    detalle del lead (ej. "Datos de la oferta", "Datos Laborales"). "Datos
    del cliente" se crea sola con cada CampaignType (es_obligatoria=True) y
    no se puede eliminar — es donde vive la identidad del cliente."""

    campaign_type = models.ForeignKey(CampaignType, on_delete=models.CASCADE, related_name="secciones")
    nombre = models.CharField(max_length=100)
    orden = models.PositiveSmallIntegerField(default=0)
    es_obligatoria = models.BooleanField(
        default=False, help_text="Sección del sistema (ej. 'Datos del cliente'): no se puede eliminar."
    )

    class Meta:
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(fields=["campaign_type", "nombre"], name="unique_campaign_type_seccion_nombre")
        ]
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"

    def __str__(self):
        return f"{self.campaign_type} · {self.nombre}"


SECCION_DATOS_CLIENTE = "Datos del cliente"


class CampaignFieldDataType(models.TextChoices):
    TEXTO = "TEXTO", "Texto"
    NUMERO = "NUMERO", "Número"
    FECHA = "FECHA", "Fecha"
    BOOLEANO = "BOOLEANO", "Booleano"
    SELECT = "SELECT", "Selección única"
    MULTISELECT = "MULTISELECT", "Selección múltiple"


class CampaignFieldOrigen(models.TextChoices):
    """De dónde sale el valor de este campo. CARGA es el caso de siempre
    (viene del archivo subido). CAPTURA_GESTION es para campañas de
    actualización de datos: el campo no se carga, se llena en el momento
    de gestionar/llamar — ver apps.leads.models.CaptureEntry."""

    CARGA = "CARGA", "Se carga desde el archivo"
    CAPTURA_GESTION = "CAPTURA_GESTION", "Se captura al gestionar"


class CampaignFieldDefinition(TimeStampedModel):
    """Define un campo dinámico de `Lead.atributos` (si origen=CARGA) o de
    `Lead.atributos_captura` (si origen=CAPTURA_GESTION) para un
    CampaignType: cómo se valida, y cómo se renderiza."""

    campaign_type = models.ForeignKey(CampaignType, on_delete=models.CASCADE, related_name="field_definitions")
    field_key = models.SlugField(max_length=100)
    label = models.CharField(max_length=150)
    data_type = models.CharField(max_length=20, choices=CampaignFieldDataType.choices)
    origen = models.CharField(max_length=20, choices=CampaignFieldOrigen.choices, default=CampaignFieldOrigen.CARGA)
    required = models.BooleanField(default=False)
    options = models.JSONField(
        null=True, blank=True, help_text="Lista de opciones. Requerido para SELECT/MULTISELECT."
    )
    orden = models.PositiveSmallIntegerField(default=0)
    mostrar_en_tabla = models.BooleanField(default=True)
    mostrar_en_detalle = models.BooleanField(default=True)
    seccion = models.ForeignKey(CampaignSection, on_delete=models.CASCADE, related_name="campos")

    # A lo sumo un campo por CampaignType puede tener cada bandera en True
    # (ver CampaignFieldDefinitionSerializer.validate) — es lo que le permite
    # al admin diseñar el esquema completo sin perder 3 comportamientos que
    # el sistema necesita resolver igual sin importar cómo se llamen los
    # campos en cada campaña: qué mostrar como nombre, con qué llamar, y
    # sobre todo con qué identificar de forma única a la persona.
    es_nombre_cliente = models.BooleanField(
        default=False, help_text="Este campo alimenta Lead.cliente_nombre (mostrado en listados)."
    )
    es_telefono_contacto = models.BooleanField(
        default=False, help_text="Este campo alimenta Lead.telefono (para llamar — ya NO se usa para el dedup)."
    )
    es_documento_identidad = models.BooleanField(
        default=False,
        help_text=(
            "Este campo alimenta Lead.documento_identidad (DNI/RUC/código de cliente) — "
            "es la clave real del dedup al cargar, porque el teléfono se recicla entre "
            "personas y el nombre puede repetirse (homónimos)."
        ),
    )

    class Meta:
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(fields=["campaign_type", "field_key"], name="unique_campaign_type_field_key")
        ]
        verbose_name = "Definición de campo"
        verbose_name_plural = "Definiciones de campo"

    def __str__(self):
        return f"{self.campaign_type} · {self.label}"


class LoteEstado(models.TextChoices):
    PROCESANDO = "PROCESANDO", "Procesando"
    COMPLETADO = "COMPLETADO", "Completado"
    ERROR = "ERROR", "Error"


class LoteCarga(TimeStampedModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="lotes_carga")
    usuario_carga = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="lotes_cargados")
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to="lotes_carga/%Y/%m/")
    cantidad_registros = models.PositiveIntegerField(default=0)
    producto = models.CharField(max_length=150, blank=True)
    agencia_restriccion = models.ForeignKey(
        "geo.Agencia", on_delete=models.SET_NULL, null=True, blank=True, related_name="lotes_restringidos"
    )
    distrito_restriccion = models.ForeignKey(
        "geo.Territorio", on_delete=models.SET_NULL, null=True, blank=True, related_name="lotes_restringidos"
    )
    estado = models.CharField(max_length=12, choices=LoteEstado.choices, default=LoteEstado.PROCESANDO)
    errores = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lote de carga"
        verbose_name_plural = "Lotes de carga"

    def __str__(self):
        return f"{self.nombre_archivo} ({self.campaign})"
