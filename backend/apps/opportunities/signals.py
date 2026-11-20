from apps.audit.signals import audit_model

from .models import Opportunity

audit_model(Opportunity)
