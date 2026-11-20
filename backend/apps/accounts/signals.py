from apps.audit.signals import audit_model

from .models import Division, User, UserAgencia, UserTerritorio

audit_model(User)
audit_model(Division)
audit_model(UserAgencia)
audit_model(UserTerritorio)
