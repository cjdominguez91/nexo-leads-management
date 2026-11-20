from apps.audit.signals import audit_model

from .models import Agencia, Territorio

audit_model(Territorio)
audit_model(Agencia)
