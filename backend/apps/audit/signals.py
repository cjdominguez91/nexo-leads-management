from django.db.models.signals import post_delete, post_save, pre_save
from django.forms.models import model_to_dict

from .models import AuditAction
from .utils import log_action

SENSITIVE_FIELDS = {"password"}


def audit_model(model):
    """Conecta post_save/post_delete de `model` para escribir en AuditLog
    automáticamente. Se usa una vez por modelo, típicamente en el
    `signals.py` de la app dueña del modelo (ver apps.accounts.signals)."""

    def _pre_save(sender, instance, **kwargs):
        instance._audit_before = None
        if instance.pk:
            try:
                instance._audit_before = _safe_dict(sender.objects.get(pk=instance.pk))
            except sender.DoesNotExist:
                pass

    def _post_save(sender, instance, created, **kwargs):
        log_action(
            accion=AuditAction.CREATE if created else AuditAction.UPDATE,
            instance=instance,
            datos_antes=getattr(instance, "_audit_before", None),
            datos_despues=_safe_dict(instance),
        )

    def _post_delete(sender, instance, **kwargs):
        log_action(accion=AuditAction.DELETE, instance=instance, datos_antes=_safe_dict(instance))

    pre_save.connect(_pre_save, sender=model, weak=False)
    post_save.connect(_post_save, sender=model, weak=False)
    post_delete.connect(_post_delete, sender=model, weak=False)


def _safe_dict(instance):
    data = model_to_dict(instance)
    for field in SENSITIVE_FIELDS:
        data.pop(field, None)
    return {
        key: value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
        for key, value in data.items()
    }
