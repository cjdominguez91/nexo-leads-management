"""Cálculo de alcance territorial por usuario.

Punto único de verdad para "qué agencias/distritos/usuarios puede ver u
operar cada rol". Cualquier endpoint que filtre por agencia o distrito debe
apoyarse en estas funciones en vez de reimplementar la regla — así, cuando
cambie el modelo de alcance (como el paso de Jefe 1-agencia a Jefe N-agencias
en esta migración), solo hay un lugar que tocar.

Checklist de consumidores esperados a medida que se agreguen fases:
- [Fase 1] apps.accounts: listado de usuarios visibles para un JEFE/SUPERVISOR.
- [Fase 2] apps.leads: queryset de Lead, reglas de asignación, endpoint de reasignación.
- [Fase 5] apps.dashboards: agregaciones filtradas por scope.
"""

from django.db.models import Q

from apps.accounts.constants import RoleNames


def agencias_visibles_para(user):
    from apps.geo.models import Agencia

    if user.is_superuser or _role(user) in (RoleNames.ADMIN, RoleNames.GERENTE):
        return Agencia.objects.filter(activo=True)

    if _role(user) == RoleNames.SUPERVISOR:
        return Agencia.objects.filter(
            territorio__in=territorios_visibles_para(user),
            activo=True,
        ).distinct()

    if _role(user) in (RoleNames.JEFE, RoleNames.SUBJEFE):
        return Agencia.objects.filter(
            asignaciones_usuario__usuario=user,
            asignaciones_usuario__activo=True,
            activo=True,
        ).distinct()

    if _role(user) == RoleNames.EJECUTIVO:
        return Agencia.objects.filter(pk=user.agencia_principal_id, activo=True)

    return Agencia.objects.none()


def territorios_visibles_para(user):
    from apps.geo.models import Territorio

    if user.is_superuser or _role(user) in (RoleNames.ADMIN, RoleNames.GERENTE):
        return Territorio.objects.filter(activo=True)

    if _role(user) == RoleNames.SUPERVISOR:
        return Territorio.objects.filter(
            asignaciones_usuario__usuario=user,
            asignaciones_usuario__activo=True,
            activo=True,
        ).distinct()

    if _role(user) in (RoleNames.JEFE, RoleNames.SUBJEFE):
        return Territorio.objects.filter(
            agencias__in=agencias_visibles_para(user),
            activo=True,
        ).distinct()

    if _role(user) == RoleNames.EJECUTIVO and user.agencia_principal_id:
        return Territorio.objects.filter(pk=user.agencia_principal.territorio_id)

    return Territorio.objects.none()


def usuarios_visibles_para(user):
    """Usuarios que `user` puede listar/gestionar según su rol y scope."""
    from apps.accounts.models import User

    if user.is_superuser or _role(user) in (RoleNames.ADMIN, RoleNames.GERENTE):
        return User.objects.all()

    if _role(user) in (RoleNames.SUPERVISOR, RoleNames.JEFE, RoleNames.SUBJEFE):
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
    """Campañas que `user` puede ver/gestionar: división del usuario ==
    división de la campaña (regla original), combinado con la restricción
    opcional por agencia/distrito de la campaña (nueva) — si la campaña no
    define `agencias_habilitadas`/`distritos_habilitados`, queda abierta a
    todo el scope normal del rol; si los define, hay que estar dentro."""
    from apps.campaigns.models import Campaign

    if user.is_superuser or _role(user) in (RoleNames.ADMIN, RoleNames.GERENTE):
        return Campaign.objects.all()

    qs = Campaign.objects.filter(division_id=user.division_id)

    agencias = agencias_visibles_para(user)
    territorios = territorios_visibles_para(user)

    return (
        qs.filter(Q(agencias_habilitadas__isnull=True) | Q(agencias_habilitadas__in=agencias))
        .filter(Q(distritos_habilitados__isnull=True) | Q(distritos_habilitados__in=territorios))
        .distinct()
    )


def _role(user):
    return getattr(user.role, "nombre", None) if getattr(user, "role_id", None) else None
