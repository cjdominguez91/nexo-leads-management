"""Cálculo de alcance por usuario.

Punto único de verdad para "qué divisiones/agencias/distritos/usuarios/
campañas puede ver u operar cada rol". Cualquier endpoint que filtre por
división, agencia o distrito debe apoyarse en estas funciones en vez de
reimplementar la regla — así, cuando cambie el modelo de alcance, solo hay
un lugar que tocar.

El alcance tiene dos ejes, que se combinan con AND:

1. División. Solo ADMIN (y superusuario) ve todas. Cualquier otro rol queda
   confinado a `user.division`; si no tiene división, no ve nada (falla
   cerrado, nunca abierto).
2. Territorio, dentro de esa división:
   - ADMIN_DIVISION / GERENTE: todo el territorio de su división.
   - SUPERVISOR: sus distritos (UserTerritorio).
   - JEFE / SUBJEFE: sus agencias (UserAgencia).
   - EJECUTIVO: su agencia_principal.

Consumidores (checklist para verificar que ningún endpoint quede sin el
filtro de división):
- apps.accounts: UserViewSet, DivisionViewSet, asignación de agencias/distritos.
- apps.geo: TerritorioViewSet, AgenciaViewSet.
- apps.campaigns: CampaignType/FieldDefinition/Section/Campaign/LoteCarga.
- apps.leads: Category/SubCategory, leads_visibles_para, reasignación,
  tipificación, prospectos, carga masiva (tasks._parse_row).
- apps.opportunities y apps.dashboards: vía leads_visibles_para.
- apps.audit: AuditLogViewSet.
"""

from django.db.models import Q

from apps.accounts.constants import DIVISION_SCOPE_ROLES, RoleNames


# ── Eje 1: división ──────────────────────────────────────────────────────


def es_global(user) -> bool:
    """¿Cruza divisiones? Solo superusuario y ADMIN."""
    return bool(user.is_superuser or _role(user) == RoleNames.ADMIN)


def filtrar_por_division(qs, user, campo: str = "division"):
    """Restringe `qs` a la división del usuario usando el lookup `campo`
    (ej. "division", "territorio__division", "category__division").
    Usuarios globales ven todo; un usuario no global sin división no ve nada."""
    if es_global(user):
        return qs
    if not user.division_id:
        return qs.none()
    return qs.filter(**{f"{campo}_id": user.division_id})


def misma_division(user, division_id) -> bool:
    """¿Puede `user` operar sobre algo de `division_id`?"""
    return es_global(user) or (user.division_id is not None and user.division_id == division_id)


# ── Eje 2: territorio (siempre dentro del eje 1) ─────────────────────────


def agencias_visibles_para(user):
    from apps.geo.models import Agencia

    base = filtrar_por_division(Agencia.objects.filter(activo=True), user, "territorio__division")
    rol = _role(user)

    if es_global(user) or rol in DIVISION_SCOPE_ROLES:
        return base

    if rol == RoleNames.SUPERVISOR:
        return base.filter(territorio__in=territorios_visibles_para(user)).distinct()

    if rol in (RoleNames.JEFE, RoleNames.SUBJEFE):
        return base.filter(
            asignaciones_usuario__usuario=user,
            asignaciones_usuario__activo=True,
        ).distinct()

    if rol == RoleNames.EJECUTIVO:
        return base.filter(pk=user.agencia_principal_id)

    return Agencia.objects.none()


def territorios_visibles_para(user):
    from apps.geo.models import Territorio

    base = filtrar_por_division(Territorio.objects.filter(activo=True), user)
    rol = _role(user)

    if es_global(user) or rol in DIVISION_SCOPE_ROLES:
        return base

    if rol == RoleNames.SUPERVISOR:
        return base.filter(
            asignaciones_usuario__usuario=user,
            asignaciones_usuario__activo=True,
        ).distinct()

    if rol in (RoleNames.JEFE, RoleNames.SUBJEFE):
        return base.filter(agencias__in=agencias_visibles_para(user)).distinct()

    if rol == RoleNames.EJECUTIVO and user.agencia_principal_id:
        return base.filter(pk=user.agencia_principal.territorio_id)

    return Territorio.objects.none()


def usuarios_visibles_para(user):
    """Usuarios que `user` puede listar/asignar según su rol y alcance."""
    from apps.accounts.models import User

    rol = _role(user)

    if es_global(user):
        return User.objects.all()

    if rol in DIVISION_SCOPE_ROLES:
        return filtrar_por_division(User.objects.all(), user)

    if rol in (RoleNames.SUPERVISOR, RoleNames.JEFE, RoleNames.SUBJEFE):
        # Incluye al propio usuario: un JEFE/SUPERVISOR no tiene agencia_principal
        # (eso es solo de EJECUTIVO), pero también puede ser responsable directo
        # de un lead/oportunidad (gestiona dentro de su scope), así que debe
        # verse a sí mismo en su propio "equipo" — si no, queda fuera de su
        # propia queryset de Opportunity/Lead apenas se auto-asigna algo.
        agencias = agencias_visibles_para(user)
        return User.objects.filter(Q(agencia_principal__in=agencias) | Q(pk=user.pk)).distinct()

    # EJECUTIVO no gestiona otros usuarios; solo se ve a sí mismo.
    return User.objects.filter(pk=user.pk)


def campanas_visibles_para(user):
    """Campañas que `user` puede ver/gestionar: de su división (eje 1),
    combinado con la restricción opcional por agencia/distrito de la campaña
    — si la campaña no define `agencias_habilitadas`/`distritos_habilitados`,
    queda abierta a todo el alcance territorial del rol; si los define, hay
    que estar dentro."""
    from apps.campaigns.models import Campaign

    qs = filtrar_por_division(Campaign.objects.all(), user)
    if es_global(user) or _role(user) in DIVISION_SCOPE_ROLES:
        return qs

    agencias = agencias_visibles_para(user)
    territorios = territorios_visibles_para(user)

    return (
        qs.filter(Q(agencias_habilitadas__isnull=True) | Q(agencias_habilitadas__in=agencias))
        .filter(Q(distritos_habilitados__isnull=True) | Q(distritos_habilitados__in=territorios))
        .distinct()
    )


def _role(user):
    return getattr(user.role, "nombre", None) if getattr(user, "role_id", None) else None
