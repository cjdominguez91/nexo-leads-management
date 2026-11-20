"""Aislamiento por División.

Escenario: dos divisiones (A y B), cada una con su distrito, agencia, tipo
de campaña, campaña, categoría y un lead. Se verifica que ADMIN_DIVISION y
GERENTE de A nunca vean ni toquen nada de B, y que ADMIN global sí vea todo.
"""

import datetime

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Division, Role, User
from apps.campaigns.models import Campaign, CampaignType
from apps.geo.models import Agencia, Territorio
from apps.leads.models import Category, Lead

pytestmark = pytest.mark.django_db


def _usuario(email, rol, division=None, **extra):
    return User.objects.create_user(
        email=email, password="x", role=Role.objects.get(nombre=rol), division=division, **extra
    )


def _division(sufijo):
    division = Division.objects.create(nombre=f"Div {sufijo}", codigo=f"D{sufijo}")
    territorio = Territorio.objects.create(nombre=f"Distrito {sufijo}", codigo=f"T{sufijo}", division=division)
    agencia = Agencia.objects.create(nombre=f"Agencia {sufijo}", codigo=f"A{sufijo}", territorio=territorio)
    tipo = CampaignType.objects.create(nombre="Créditos", categoria="VENTAS", division=division)
    campana = Campaign.objects.create(
        nombre=f"Campaña {sufijo}", campaign_type=tipo, division=division, fecha_inicio=datetime.date.today()
    )
    categoria = Category.objects.create(nombre=f"Contacto {sufijo}", division=division)
    lead = Lead.objects.create(campaign=campana, agencia=agencia, distrito=territorio, documento_identidad=f"DOC{sufijo}")
    return {
        "division": division,
        "territorio": territorio,
        "agencia": agencia,
        "tipo": tipo,
        "campana": campana,
        "categoria": categoria,
        "lead": lead,
    }


@pytest.fixture
def mundo():
    a, b = _division("A"), _division("B")
    return {
        "A": a,
        "B": b,
        "admin": _usuario("admin@x.com", "ADMIN"),
        "admin_div_a": _usuario("admdiv@a.com", "ADMIN_DIVISION", a["division"]),
        "admin_div_a2": _usuario("admdiv2@a.com", "ADMIN_DIVISION", a["division"]),
        "gerente_a": _usuario("gerente@a.com", "GERENTE", a["division"]),
        "ejecutivo_b": _usuario("ejec@b.com", "EJECUTIVO", b["division"], agencia_principal=b["agencia"]),
    }


def _cliente(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _ids(response):
    data = response.json()
    rows = data["results"] if isinstance(data, dict) and "results" in data else data
    return {row["id"] for row in rows}


# ── Lectura: cada catálogo solo muestra la propia división ──────────────


@pytest.mark.parametrize(
    "url, clave",
    [
        ("/api/geo/territorios/", "territorio"),
        ("/api/geo/agencias/", "agencia"),
        ("/api/campaigns/campaign-types/", "tipo"),
        ("/api/campaigns/campaigns/", "campana"),
        ("/api/leads/categories/", "categoria"),
        ("/api/leads/leads/", "lead"),
    ],
)
@pytest.mark.parametrize("actor", ["admin_div_a", "gerente_a"])
def test_roles_de_division_solo_ven_su_division(mundo, url, clave, actor):
    ids = _ids(_cliente(mundo[actor]).get(url))
    assert mundo["A"][clave].id in ids
    assert mundo["B"][clave].id not in ids


def test_admin_global_ve_todas_las_divisiones(mundo):
    ids = _ids(_cliente(mundo["admin"]).get("/api/geo/territorios/"))
    assert {mundo["A"]["territorio"].id, mundo["B"]["territorio"].id} <= ids


def test_admin_division_no_lee_detalle_de_otra_division(mundo):
    response = _cliente(mundo["admin_div_a"]).get(f"/api/geo/agencias/{mundo['B']['agencia'].id}/")
    assert response.status_code == 404


# ── Escritura de catálogos ──────────────────────────────────────────────


def test_admin_division_crea_distrito_siempre_en_su_division(mundo):
    response = _cliente(mundo["admin_div_a"]).post(
        "/api/geo/territorios/",
        {"nombre": "Nuevo", "codigo": "TNEW", "division": mundo["B"]["division"].id},
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert Territorio.objects.get(codigo="TNEW").division_id == mundo["A"]["division"].id


def test_admin_division_no_crea_agencia_en_distrito_ajeno(mundo):
    response = _cliente(mundo["admin_div_a"]).post(
        "/api/geo/agencias/",
        {"nombre": "Intrusa", "codigo": "AX", "territorio": mundo["B"]["territorio"].id},
        format="json",
    )
    assert response.status_code == 400


def test_admin_division_no_edita_catalogo_ajeno(mundo):
    response = _cliente(mundo["admin_div_a"]).patch(
        f"/api/leads/categories/{mundo['B']['categoria'].id}/", {"nombre": "Hackeada"}, format="json"
    )
    assert response.status_code == 404


def test_admin_division_no_crea_divisiones(mundo):
    response = _cliente(mundo["admin_div_a"]).post(
        "/api/auth/divisions/", {"nombre": "Nueva", "codigo": "NEW"}, format="json"
    )
    assert response.status_code == 403


def test_campana_no_acepta_tipo_de_otra_division(mundo):
    response = _cliente(mundo["admin"]).post(
        "/api/campaigns/campaigns/",
        {
            "nombre": "Mezclada",
            "campaign_type": mundo["B"]["tipo"].id,
            "division": mundo["A"]["division"].id,
            "fecha_inicio": str(datetime.date.today()),
        },
        format="json",
    )
    assert response.status_code == 400
    assert "campaign_type" in response.json()


def test_mismo_nombre_de_tipo_en_dos_divisiones_es_valido(mundo):
    # Ambas divisiones ya tienen un "Créditos" (fixture): no debe chocar.
    assert CampaignType.objects.filter(nombre="Créditos").count() == 2


# ── Usuarios ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("rol", ["ADMIN", "ADMIN_DIVISION"])
def test_admin_division_no_puede_crear_roles_de_administracion(mundo, rol):
    response = _cliente(mundo["admin_div_a"]).post(
        "/api/auth/users/",
        {"email": f"nuevo-{rol}@a.com", "codigo_empleado": f"E-{rol}", "role": Role.objects.get(nombre=rol).id},
        format="json",
    )
    assert response.status_code == 400
    assert "role" in response.json()


def test_admin_division_crea_usuario_en_su_division(mundo):
    response = _cliente(mundo["admin_div_a"]).post(
        "/api/auth/users/",
        {
            "email": "sup@a.com",
            "codigo_empleado": "E1",
            "role": Role.objects.get(nombre="SUPERVISOR").id,
            "division": mundo["B"]["division"].id,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert User.objects.get(email="sup@a.com").division_id == mundo["A"]["division"].id


def test_admin_division_no_ve_usuarios_de_otra_division(mundo):
    client = _cliente(mundo["admin_div_a"])
    emails = {u["email"] for u in client.get("/api/auth/users/").json()["results"]}
    assert "ejec@b.com" not in emails
    assert "admin@x.com" not in emails
    assert client.patch(f"/api/auth/users/{mundo['ejecutivo_b'].id}/", {"first_name": "X"}, format="json").status_code == 404


def test_admin_division_no_modifica_a_otro_admin_division(mundo):
    response = _cliente(mundo["admin_div_a"]).patch(
        f"/api/auth/users/{mundo['admin_div_a2'].id}/", {"is_active": False}, format="json"
    )
    assert response.status_code == 403


def test_admin_division_no_se_auto_escala(mundo):
    actor = mundo["admin_div_a"]
    response = _cliente(actor).patch(
        f"/api/auth/users/{actor.id}/", {"role": Role.objects.get(nombre="ADMIN").id}, format="json"
    )
    assert response.status_code == 403
    actor.refresh_from_db()
    assert actor.role.nombre == "ADMIN_DIVISION"


def test_no_se_asigna_agencia_de_otra_division_a_un_usuario(mundo):
    jefe = _usuario("jefe@a.com", "JEFE", mundo["A"]["division"])
    response = _cliente(mundo["admin"]).post(
        f"/api/auth/users/{jefe.id}/agencias/", {"agencia": mundo["B"]["agencia"].id}, format="json"
    )
    assert response.status_code == 400


# ── Operación ───────────────────────────────────────────────────────────


def test_no_se_tipifica_con_categoria_de_otra_division(mundo):
    response = _cliente(mundo["admin"]).post(
        f"/api/leads/leads/{mundo['A']['lead'].id}/gestionar/",
        {"category": mundo["B"]["categoria"].id, "comentario": "x"},
        format="json",
    )
    assert response.status_code == 400
    assert "category" in response.json()


def test_no_se_reasigna_lead_a_otra_division(mundo):
    response = _cliente(mundo["admin"]).post(
        f"/api/leads/leads/{mundo['A']['lead'].id}/asignar/",
        {"usuario_destino": mundo["ejecutivo_b"].id},
        format="json",
    )
    assert response.status_code == 403
