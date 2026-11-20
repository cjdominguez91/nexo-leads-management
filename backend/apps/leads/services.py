"""Lógica de asignación de leads. Vive fuera de las vistas porque la reglas
de scope (quién puede asignar a quién, cuándo se permite cruzar de agencia)
son las más delicadas del sistema — se prueban por separado de la capa HTTP.
"""

from datetime import datetime

from django.utils import timezone
from django.db import transaction

from apps.accounts.constants import DIVISION_SCOPE_ROLES, RoleNames
from apps.accounts.models import User
from apps.campaigns.models import CampaignFieldOrigen, CampaignModoCarga
from apps.campaigns.services import resolver_campos_especiales
from apps.campaigns.validators import AtributosValidationError, validate_atributos
from apps.core.scoping import (
    agencias_visibles_para,
    campanas_visibles_para,
    es_global,
    filtrar_por_division,
    territorios_visibles_para,
    usuarios_visibles_para,
)
from apps.notifications.services import notificar_asignacion

from .models import Assignment, CaptureEntry, Category, Lead, LeadEstado, ManagementLog, SubCategory, SubCategoryEfecto


class AssignmentError(Exception):
    """Regla de negocio violada al asignar (se traduce a 403 en la vista)."""


class ProspectoError(Exception):
    """Error de validación/alcance al registrar un prospecto a mano (se
    traduce a 400 en la vista)."""


class ProspectoYaExisteError(Exception):
    """El documento ya existe en esta Prospección y la última gestión (o el
    registro, si nunca se gestionó) fue hace menos de
    DIAS_INACTIVIDAD_PARA_RECLAMAR días — no se reclama automáticamente,
    hay que avisarle a quien lo intenta cargar quién lo tiene (se traduce a
    409 en la vista)."""

    def __init__(self, lead: Lead):
        self.lead = lead
        super().__init__("Este cliente ya se encuentra prospectado.")


def _role(user):
    return getattr(user.role, "nombre", None) if getattr(user, "role_id", None) else None


def leads_visibles_para(user):
    """Leads que `user` puede ver/gestionar según su rol y scope. Punto
    único de verdad reusado también por apps.opportunities (una Opportunity
    es visible si su Lead lo es)."""

    qs = Lead.objects.all()
    if es_global(user):
        return qs
    if _role(user) in DIVISION_SCOPE_ROLES:
        # Todo el territorio, pero solo de su división (vía la campaña, que
        # es la dueña de la división del lead).
        return filtrar_por_division(qs, user, "campaign__division")
    campanas = campanas_visibles_para(user)
    if _role(user) == RoleNames.EJECUTIVO:
        return qs.filter(usuario_asignado=user, campaign__in=campanas)
    return qs.filter(agencia__in=agencias_visibles_para(user), campaign__in=campanas)


def reasignar_lead(*, lead: Lead, usuario_destino: User, asignado_por: User, notificar: bool = True) -> Assignment:
    """`notificar=False` lo usa la asignación masiva: no queremos una
    notificación por cada lead del lote, sino una sola agregada — el
    llamador (la vista) se encarga de mandarla al final, agrupada."""

    if not (asignado_por.is_superuser or lead.agencia_id in agencias_visibles_para(asignado_por).values_list("id", flat=True)):
        raise AssignmentError("No tienes alcance sobre la agencia actual de este lead.")

    if not (asignado_por.is_superuser or usuario_destino.pk in usuarios_visibles_para(asignado_por).values_list("pk", flat=True)):
        raise AssignmentError("El usuario destino está fuera de tu alcance.")

    agencia_destino = usuario_destino.agencia_principal or lead.agencia

    # Un lead nunca sale de la división de su campaña, ni siquiera por un
    # ADMIN global: la agencia destino debe ser de esa misma división.
    if agencia_destino.territorio.division_id != lead.campaign.division_id:
        raise AssignmentError("El usuario destino pertenece a una agencia de otra división.")

    if _cambia_agencia(lead, agencia_destino) and not asignado_por.is_superuser and _role(asignado_por) == RoleNames.SUPERVISOR:
        territorios_ids = set(territorios_visibles_para(asignado_por).values_list("id", flat=True))
        if agencia_destino.territorio_id not in territorios_ids:
            raise AssignmentError("Como SUPERVISOR solo puedes reasignar dentro de tu(s) propio(s) distrito(s).")

    with transaction.atomic():
        locked_lead = Lead.objects.select_for_update().get(pk=lead.pk)
        hubo_cambio_agencia = _cambia_agencia(locked_lead, agencia_destino)

        assignment = Assignment.objects.create(
            lead=locked_lead,
            usuario_origen=locked_lead.usuario_asignado,
            usuario_destino=usuario_destino,
            agencia_origen=locked_lead.agencia,
            agencia_destino=agencia_destino if hubo_cambio_agencia else None,
            asignado_por=asignado_por,
        )

        locked_lead.usuario_asignado = usuario_destino
        locked_lead.fecha_asignacion = timezone.now()
        locked_lead.agencia = agencia_destino
        locked_lead.distrito = agencia_destino.territorio
        if locked_lead.estado == LeadEstado.NUEVO:
            locked_lead.estado = LeadEstado.ASIGNADO
        locked_lead.save(update_fields=["usuario_asignado", "fecha_asignacion", "agencia", "distrito", "estado"])

        if notificar:
            # Post-commit: si la transacción se revierte, no queremos haber
            # empujado una notificación de algo que nunca pasó.
            transaction.on_commit(
                lambda: notificar_asignacion(
                    usuario_destino_id=usuario_destino.id,
                    campaign=locked_lead.campaign,
                    cantidad=1,
                    motivo="reasignación",
                )
            )

    return assignment


def _cambia_agencia(lead: Lead, agencia_destino) -> bool:
    return lead.agencia_id != agencia_destino.id


_EFECTO_A_LEAD_ESTADO = {
    SubCategoryEfecto.SIN_EFECTO: LeadEstado.GESTIONADO,
    SubCategoryEfecto.ABRE_OPORTUNIDAD: LeadEstado.GESTIONADO,
    SubCategoryEfecto.GANADA: LeadEstado.GANADO,
    SubCategoryEfecto.PERDIDA: LeadEstado.PERDIDO,
}


def tipificar_lead(
    *,
    lead: Lead,
    usuario: User,
    category: Category,
    subcategory: SubCategory | None,
    comentario: str,
    fecha_proximo_contacto: datetime | None = None,
    datos_captura: dict | None = None,
):
    """Crea el ManagementLog (inmutable) y aplica el efecto *transversal* de
    la subcategoría (`SubCategoryEfecto`) sobre el Lead y su Opportunity a
    la vez — es un solo interruptor, no dos mecanismos separados:

    - SIN_EFECTO: solo queda el registro de gestión, Lead -> GESTIONADO.
    - ABRE_OPORTUNIDAD: Lead -> GESTIONADO; se crea la Opportunity si no
      existe una ya en progreso para este lead (queda EN_PROGRESO).
    - GANADA / PERDIDA: Lead -> GANADO/PERDIDO; se crea la Opportunity si
      hace falta (ej. venta directa sin pasar por "Lo Pensará") y se cierra
      con ese mismo resultado.

    Si `datos_captura` trae al menos un valor no vacío (campañas de
    actualización de datos, campos origen=CAPTURA_GESTION), además crea un
    CaptureEntry y hace merge sobre Lead.atributos_captura. Si llega vacío
    (el ejecutivo no contactó al cliente o no había nada que actualizar), se
    ignora por completo — no es un error, simplemente no pasó nada que capturar.

    Devuelve (log, opportunity_tocada_o_None).
    """
    efecto = subcategory.efecto if subcategory else SubCategoryEfecto.SIN_EFECTO

    with transaction.atomic():
        log = ManagementLog.objects.create(
            lead=lead,
            usuario=usuario,
            category=category,
            subcategory=subcategory,
            comentario=comentario,
            fecha_proximo_contacto=fecha_proximo_contacto,
        )

        lead.categoria_actual = category
        lead.subcategoria_actual = subcategory
        lead.fecha_ultima_gestion = log.timestamp
        lead.estado = _EFECTO_A_LEAD_ESTADO[efecto]
        update_fields = ["categoria_actual", "subcategoria_actual", "fecha_ultima_gestion", "estado"]

        if datos_captura and any(v not in (None, "", [], {}) for v in datos_captura.values()):
            cleaned = validate_atributos(lead.campaign.campaign_type, datos_captura, origen=CampaignFieldOrigen.CAPTURA_GESTION)
            CaptureEntry.objects.create(lead=lead, usuario=usuario, datos=cleaned)
            lead.atributos_captura = {**lead.atributos_captura, **cleaned}
            update_fields.append("atributos_captura")

        lead.save(update_fields=update_fields)

        opportunity = None
        if efecto != SubCategoryEfecto.SIN_EFECTO:
            opportunity = _tocar_oportunidad(
                lead=lead, usuario=usuario, efecto=efecto, fecha_proximo_contacto=fecha_proximo_contacto
            )

    return log, opportunity


DIAS_INACTIVIDAD_PARA_RECLAMAR = 30


def crear_prospecto(*, campaign, usuario: User, atributos_raw: dict, agencia=None) -> tuple[Lead, bool]:
    """Registra un prospecto uno por uno — solo para campañas cuyo
    CampaignType tiene modo_carga=INDIVIDUAL ("Prospección"). A diferencia
    de la carga masiva, aquí no hay archivo: el propio usuario que gestiona
    al cliente es quien crea el registro, y queda asignado a él de una vez.

    Agencia: si `usuario` es EJECUTIVO, se ignora `agencia` y se usa su
    agencia_principal (es la única que tiene). Para el resto de roles,
    `agencia` es obligatoria y debe estar dentro de su alcance.

    Dedup con reclamo por inactividad: si el documento ya existe en esta
    campaña, se revisa cuánto hace que se gestionó por última vez (o que se
    registró, si nunca se gestionó). Menos de DIAS_INACTIVIDAD_PARA_RECLAMAR
    días -> se rechaza (ProspectoYaExisteError), sigue "vivo" con su dueño
    actual. Más de eso -> se asume que el cliente cambió de contexto: se
    actualiza el registro existente y se reasigna al usuario que lo está
    registrando ahora, dejando constancia en Assignment igual que una
    reasignación manual. El historial de gestiones previo (ManagementLog) no
    se toca — sigue existiendo, solo cambia el dueño actual.

    Devuelve (lead, reclamado: bool).
    """

    campaign_type = campaign.campaign_type
    if campaign_type.modo_carga != CampaignModoCarga.INDIVIDUAL:
        raise ProspectoError("Este tipo de campaña no admite registro individual de prospectos.")
    if campaign.esta_cerrada:
        raise ProspectoError("Esta campaña está cerrada o vencida: no se pueden registrar prospectos nuevos.")

    nombre_field, telefono_field, documento_field = resolver_campos_especiales(campaign_type)

    if _role(usuario) == RoleNames.EJECUTIVO:
        agencia_resuelta = usuario.agencia_principal
        if agencia_resuelta is None:
            raise ProspectoError("Tu usuario no tiene una agencia asignada.")
    else:
        if agencia is None:
            raise ProspectoError("Debes elegir una agencia.")
        if not (usuario.is_superuser or agencia.id in agencias_visibles_para(usuario).values_list("id", flat=True)):
            raise ProspectoError("Esa agencia está fuera de tu alcance.")
        agencia_resuelta = agencia

    if agencia_resuelta.territorio.division_id != campaign.division_id:
        raise ProspectoError("La agencia no pertenece a la división de esta campaña.")

    cliente_nombre = str(atributos_raw.get(nombre_field.field_key) or "").strip()
    telefono = str(atributos_raw.get(telefono_field.field_key) or "").strip()
    documento_identidad = str(atributos_raw.get(documento_field.field_key) or "").strip()
    if not documento_identidad:
        raise AtributosValidationError({documento_field.field_key: "Este campo es obligatorio."})

    # Igual que en la carga masiva (apps.leads.tasks._parse_row): los 3 campos
    # especiales SÍ se validan y se guardan también en atributos (aunque ya
    # alimentan las columnas dedicadas cliente_nombre/telefono/documento_identidad
    # arriba) — si no, validate_atributos los ve "ausentes" y los rechaza
    # cuando el admin los marcó como obligatorios.
    atributos_crudos = {k: v for k, v in atributos_raw.items() if v not in (None, "")}
    atributos = validate_atributos(campaign_type, atributos_crudos, origen=CampaignFieldOrigen.CARGA)

    with transaction.atomic():
        existente = (
            Lead.objects.select_for_update()
            .filter(campaign=campaign, documento_identidad=documento_identidad)
            .first()
        )

        if existente is None:
            lead = Lead.objects.create(
                campaign=campaign,
                lote_carga=None,
                cliente_nombre=cliente_nombre,
                telefono=telefono,
                documento_identidad=documento_identidad,
                agencia=agencia_resuelta,
                distrito=agencia_resuelta.territorio,
                usuario_asignado=usuario,
                fecha_asignacion=timezone.now(),
                estado=LeadEstado.ASIGNADO,
                atributos=atributos,
            )
            return lead, False

        referencia = existente.fecha_ultima_gestion or existente.created_at
        dias_inactivo = (timezone.now() - referencia).days
        if dias_inactivo < DIAS_INACTIVIDAD_PARA_RECLAMAR:
            raise ProspectoYaExisteError(existente)

        hubo_cambio_agencia = existente.agencia_id != agencia_resuelta.id
        Assignment.objects.create(
            lead=existente,
            usuario_origen=existente.usuario_asignado,
            usuario_destino=usuario,
            agencia_origen=existente.agencia,
            agencia_destino=agencia_resuelta if hubo_cambio_agencia else None,
            asignado_por=usuario,
        )

        existente.cliente_nombre = cliente_nombre
        existente.telefono = telefono
        existente.agencia = agencia_resuelta
        existente.distrito = agencia_resuelta.territorio
        existente.usuario_asignado = usuario
        existente.fecha_asignacion = timezone.now()
        existente.estado = LeadEstado.ASIGNADO
        existente.categoria_actual = None
        existente.subcategoria_actual = None
        existente.atributos = atributos
        existente.save(
            update_fields=[
                "cliente_nombre",
                "telefono",
                "agencia",
                "distrito",
                "usuario_asignado",
                "fecha_asignacion",
                "estado",
                "categoria_actual",
                "subcategoria_actual",
                "atributos",
            ]
        )

        transaction.on_commit(
            lambda: notificar_asignacion(
                usuario_destino_id=usuario.id,
                campaign=campaign,
                cantidad=1,
                motivo="reclamo por inactividad (prospección)",
            )
        )

        return existente, True


def _tocar_oportunidad(*, lead: Lead, usuario: User, efecto: str, fecha_proximo_contacto):
    from apps.notifications.models import NotificationTipo
    from apps.notifications.services import notificar_oportunidad
    from apps.opportunities.models import Opportunity, OpportunityEstado

    opportunity = Opportunity.objects.filter(lead=lead, estado=OpportunityEstado.EN_PROGRESO).first()
    creada = opportunity is None
    if opportunity is None:
        opportunity = Opportunity.objects.create(
            lead=lead,
            campaign=lead.campaign,
            usuario_responsable=lead.usuario_asignado or usuario,
        )

    campos = []
    if fecha_proximo_contacto is not None:
        opportunity.fecha_proximo_contacto = fecha_proximo_contacto
        campos.append("fecha_proximo_contacto")

    cerrada = efecto in (SubCategoryEfecto.GANADA, SubCategoryEfecto.PERDIDA)
    if efecto == SubCategoryEfecto.GANADA:
        opportunity.estado = OpportunityEstado.GANADA
        opportunity.fecha_cierre = timezone.now()
        campos += ["estado", "fecha_cierre"]
    elif efecto == SubCategoryEfecto.PERDIDA:
        opportunity.estado = OpportunityEstado.PERDIDA
        opportunity.fecha_cierre = timezone.now()
        campos += ["estado", "fecha_cierre"]

    if campos:
        opportunity.save(update_fields=campos)

    # Solo se notifica si fue OTRA persona quien gestionó en nombre del
    # responsable (JEFE/SUPERVISOR tipificando dentro de su scope) — si el
    # propio responsable es quien tipificó, notificarlo sería ruido de su
    # propia acción (ver docstring de apps.notifications.services).
    if opportunity.usuario_responsable_id != usuario.id:
        tipo_notificacion = None
        if cerrada:
            tipo_notificacion = NotificationTipo.OPORTUNIDAD_CERRADA
        elif creada:
            tipo_notificacion = NotificationTipo.OPORTUNIDAD_CREADA
        if tipo_notificacion:
            transaction.on_commit(
                lambda: notificar_oportunidad(
                    usuario_responsable_id=opportunity.usuario_responsable_id,
                    opportunity=opportunity,
                    tipo=tipo_notificacion,
                )
            )

    return opportunity
