"""Lógica compartida sobre CampaignType/CampaignFieldDefinition, reusada
tanto por la carga masiva (apps.leads.tasks) como por el registro individual
de prospectos (apps.leads.services.crear_prospecto)."""

from .models import CampaignFieldOrigen


class CamposEspecialesError(Exception):
    """El CampaignType no tiene los 3 campos especiales (nombre/teléfono/
    documento) definidos — no se puede identificar ni desduplicar clientes."""

    def __init__(self, faltantes: list[str]):
        self.faltantes = faltantes
        super().__init__(
            f"El tipo de campaña no tiene definido cuál campo es el {', el '.join(faltantes)}. "
            "Configúralo en Administración → Tipos de campaña."
        )


def resolver_campos_especiales(campaign_type):
    """Devuelve (nombre_field, telefono_field, documento_field), las
    CampaignFieldDefinition marcadas es_nombre_cliente/es_telefono_contacto/
    es_documento_identidad — siempre de origen CARGA (ver validación en
    CampaignFieldDefinitionSerializer). Lanza CamposEspecialesError si falta
    alguna."""

    campos = campaign_type.field_definitions.filter(origen=CampaignFieldOrigen.CARGA)
    nombre_field = campos.filter(es_nombre_cliente=True).first()
    telefono_field = campos.filter(es_telefono_contacto=True).first()
    documento_field = campos.filter(es_documento_identidad=True).first()

    if not nombre_field or not telefono_field or not documento_field:
        faltantes = [
            etiqueta
            for campo, etiqueta in (
                (nombre_field, "nombre del cliente"),
                (telefono_field, "teléfono de contacto"),
                (documento_field, "documento de identidad"),
            )
            if not campo
        ]
        raise CamposEspecialesError(faltantes)

    return nombre_field, telefono_field, documento_field
