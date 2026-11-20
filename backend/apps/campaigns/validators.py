"""Validación de `Lead.atributos` contra `CampaignFieldDefinition`.

Punto único usado tanto por la carga masiva (apps.leads.tasks) como por la
creación/edición manual de un lead (apps.leads serializers) — así el
esquema dinámico se valida igual sin importar el camino de entrada.
"""

from datetime import date, datetime

from .models import CampaignFieldDataType, CampaignFieldOrigen


class AtributosValidationError(Exception):
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))


def validate_atributos(campaign_type, atributos: dict, origen: str = CampaignFieldOrigen.CARGA) -> dict:
    """Valida `atributos` contra las CampaignFieldDefinition de `campaign_type`
    que tengan ese `origen` — CARGA para la carga de archivos (el caso de
    siempre), CAPTURA_GESTION para el formulario dinámico que se llena al
    gestionar un lead (ver apps.leads.services.tipificar_lead)."""

    field_definitions = campaign_type.field_definitions.filter(origen=origen)
    cleaned = {}
    errors = {}

    for field in field_definitions:
        raw_value = atributos.get(field.field_key)

        if raw_value in (None, ""):
            if field.required:
                errors[field.field_key] = "Este campo es obligatorio."
            continue

        try:
            cleaned[field.field_key] = _coerce(field, raw_value)
        except ValueError as exc:
            errors[field.field_key] = str(exc)

    unknown_keys = set(atributos) - {f.field_key for f in field_definitions}
    for key in unknown_keys:
        errors[key] = "Campo no definido para este tipo de campaña."

    if errors:
        raise AtributosValidationError(errors)

    return cleaned


def _coerce(field, value):
    data_type = field.data_type

    if data_type == CampaignFieldDataType.TEXTO:
        return str(value)

    if data_type == CampaignFieldDataType.NUMERO:
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ValueError("Debe ser un número.")

    if data_type == CampaignFieldDataType.FECHA:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        try:
            return date.fromisoformat(str(value)).isoformat()
        except ValueError:
            raise ValueError("Debe ser una fecha en formato AAAA-MM-DD.")

    if data_type == CampaignFieldDataType.BOOLEANO:
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in ("true", "1", "si", "sí", "x"):
            return True
        if str(value).strip().lower() in ("false", "0", "no", ""):
            return False
        raise ValueError("Debe ser verdadero/falso.")

    if data_type == CampaignFieldDataType.SELECT:
        options = field.options or []
        if value not in options:
            raise ValueError(f"Valor no válido. Opciones: {', '.join(options)}.")
        return value

    if data_type == CampaignFieldDataType.MULTISELECT:
        options = field.options or []
        values = value if isinstance(value, list) else [v.strip() for v in str(value).split(";") if v.strip()]
        invalid = [v for v in values if v not in options]
        if invalid:
            raise ValueError(f"Valores no válidos: {', '.join(invalid)}. Opciones: {', '.join(options)}.")
        return values

    raise ValueError(f"Tipo de dato no soportado: {data_type}")
