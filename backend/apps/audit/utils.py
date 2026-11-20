from .middleware import get_client_ip, get_current_user
from .models import AuditLog


def log_action(*, accion, instance, datos_antes=None, datos_despues=None):
    AuditLog.objects.create(
        usuario=get_current_user(),
        accion=accion,
        modelo_afectado=instance.__class__.__name__,
        id_afectado=str(instance.pk),
        datos_antes=datos_antes,
        datos_despues=datos_despues,
        ip_address=get_client_ip(),
    )
