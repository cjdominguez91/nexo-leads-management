from django.db.models import ProtectedError
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status


def exception_handler(exc, context):
    """Envuelve el manejador default de DRF: cuando se intenta borrar un
    registro que otro protege vía `on_delete=PROTECT` (ej. una Agencia con
    leads asociados), Django lanza `ProtectedError` — sin este handler,
    DRF no la reconoce y responde 500. La convertimos en 400 con un
    mensaje legible en vez de un error genérico de servidor."""

    if isinstance(exc, ProtectedError):
        cantidad = len(exc.protected_objects) if exc.protected_objects is not None else None
        detalle = "No se puede eliminar: está en uso por otros registros del sistema"
        if cantidad:
            detalle += f" ({cantidad})"
        detalle += ". Puedes desactivarlo en su lugar."
        return Response({"detail": detalle}, status=status.HTTP_400_BAD_REQUEST)

    return drf_exception_handler(exc, context)
