import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.core.scoping import campanas_visibles_para
from apps.leads.models import Lead, ManagementLog
from apps.leads.services import leads_visibles_para
from apps.opportunities.models import Opportunity


@pytest.mark.django_db
def test_seed_demo_carga_datos_y_respeta_aislamiento():
    call_command("seed_demo")

    assert Lead.objects.count() > 50
    assert ManagementLog.objects.exists()
    assert Opportunity.objects.exists()

    # Cada admin de división solo ve leads de su división.
    admin_bp = User.objects.get(email="admin.persona@demo.nexo")
    admin_be = User.objects.get(email="admin.empresas@demo.nexo")
    assert set(leads_visibles_para(admin_bp).values_list("campaign__division__codigo", flat=True)) == {"BP"}
    assert set(leads_visibles_para(admin_be).values_list("campaign__division__codigo", flat=True)) == {"BE"}

    # El ejecutivo solo ve lo suyo; el jefe multi-agencia ve sus dos agencias.
    ejecutivo = User.objects.get(email="ejecutivo1@demo.nexo")
    assert all(lead.usuario_asignado_id == ejecutivo.id for lead in leads_visibles_para(ejecutivo))
    jefe = User.objects.get(email="jefe@demo.nexo")
    assert set(leads_visibles_para(jefe).values_list("agencia__codigo", flat=True)) == {"1", "2"}
    assert campanas_visibles_para(jefe).exists()


@pytest.mark.django_db
def test_seed_demo_se_niega_si_ya_hay_leads():
    call_command("seed_demo")
    with pytest.raises(CommandError):
        call_command("seed_demo")
