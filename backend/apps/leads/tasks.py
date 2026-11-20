import csv
import io

from celery import shared_task

from apps.campaigns.models import LoteCarga, LoteEstado
from apps.campaigns.services import CamposEspecialesError, resolver_campos_especiales
from apps.campaigns.validators import AtributosValidationError, validate_atributos
from apps.geo.models import Agencia

from .models import Lead, LeadEstado

# Única columna reservada: todo lo demás (incluido "el nombre" y "el
# teléfono") lo define el admin vía CampaignFieldDefinition. agencia_codigo
# es estructural (resuelve una FK real), no un dato de negocio configurable.
CORE_FIELDS = {"agencia_codigo"}


@shared_task
def procesar_lote_carga(lote_id):
    lote = LoteCarga.objects.select_related("campaign__campaign_type", "agencia_restriccion").get(pk=lote_id)
    campaign = lote.campaign
    campaign_type = campaign.campaign_type

    try:
        nombre_field, telefono_field, documento_field = resolver_campos_especiales(campaign_type)
    except CamposEspecialesError as exc:
        lote.estado = LoteEstado.ERROR
        lote.errores = [{"fila": None, "error": str(exc)}]
        lote.save(update_fields=["estado", "errores"])
        return

    try:
        rows = _read_rows(lote.archivo)
    except ValueError as exc:
        lote.estado = LoteEstado.ERROR
        lote.errores = [{"fila": None, "error": str(exc)}]
        lote.save(update_fields=["estado", "errores"])
        return

    creados = 0
    errores = []

    for index, row in enumerate(rows, start=2):  # fila 1 = encabezado
        try:
            lead_data = _parse_row(row, lote, campaign, campaign_type, nombre_field, telefono_field, documento_field)
        except ValueError as exc:
            errores.append({"fila": index, "error": str(exc)})
            continue

        if Lead.objects.filter(campaign=campaign, documento_identidad=lead_data["documento_identidad"]).exists():
            errores.append(
                {
                    "fila": index,
                    "error": (
                        f"El documento {lead_data['documento_identidad']} ya existe en esta campaña. "
                        "Si es multi-oferta, consolida los productos en un solo registro antes de subir."
                    ),
                }
            )
            continue

        Lead.objects.create(**lead_data)
        creados += 1

    lote.cantidad_registros = creados
    lote.errores = errores or None
    lote.estado = LoteEstado.ERROR if creados == 0 and errores else LoteEstado.COMPLETADO
    lote.save(update_fields=["cantidad_registros", "errores", "estado"])


def _parse_row(
    row: dict, lote: LoteCarga, campaign, campaign_type, nombre_field, telefono_field, documento_field
) -> dict:
    # Solo el documento es obligatorio: identifica al cliente sin ambigüedad.
    # Nombre y teléfono pueden venir vacíos (ej. bases compradas que solo
    # traen el documento) — el frontend muestra el documento como respaldo
    # donde antes se habría mostrado un nombre en blanco.
    cliente_nombre = str(row.get(nombre_field.field_key) or "").strip()
    telefono = str(row.get(telefono_field.field_key) or "").strip()
    documento_identidad = str(row.get(documento_field.field_key) or "").strip()
    if not documento_identidad:
        raise ValueError(f"'{documento_field.label}' es obligatorio.")

    if lote.agencia_restriccion_id:
        agencia = lote.agencia_restriccion
    else:
        agencia_codigo = (row.get("agencia_codigo") or "").strip()
        try:
            # Solo agencias de la división de la campaña: un código de agencia
            # de otra división se reporta como inexistente para esta carga.
            agencia = Agencia.objects.select_related("territorio").get(
                codigo=agencia_codigo, activo=True, territorio__division_id=campaign.division_id
            )
        except Agencia.DoesNotExist:
            raise ValueError(f"Agencia con código '{agencia_codigo}' no existe, está inactiva o es de otra división.")

    if lote.distrito_restriccion_id and agencia.territorio_id != lote.distrito_restriccion_id:
        raise ValueError("La agencia del registro no pertenece al distrito restringido de este lote.")

    atributos_crudos = {k: v for k, v in row.items() if k not in CORE_FIELDS and v not in (None, "")}
    try:
        atributos = validate_atributos(campaign_type, atributos_crudos)
    except AtributosValidationError as exc:
        raise ValueError("; ".join(f"{k}: {v}" for k, v in exc.errors.items()))

    return {
        "campaign": campaign,
        "lote_carga": lote,
        "cliente_nombre": cliente_nombre,
        "telefono": telefono,
        "documento_identidad": documento_identidad,
        "agencia": agencia,
        "distrito": agencia.territorio,
        "atributos": atributos,
        "estado": LeadEstado.NUEVO,
    }


def _read_rows(file_field) -> list[dict]:
    name = file_field.name.lower()
    file_field.open("rb")
    try:
        content = file_field.read()
    finally:
        file_field.close()

    if name.endswith(".csv"):
        text = content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(text)))

    if name.endswith(".xlsx"):
        import openpyxl

        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        header = [str(h).strip() if h else "" for h in next(rows_iter)]
        rows = []
        for values in rows_iter:
            if all(v is None for v in values):
                continue
            rows.append({header[i]: values[i] for i in range(len(header))})
        return rows

    raise ValueError("Formato de archivo no soportado. Usa CSV o XLSX.")
