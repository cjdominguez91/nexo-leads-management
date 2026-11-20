from apps.audit.signals import audit_model

from .models import Category, SubCategory

# Lead y Assignment quedan fuera a propósito: Assignment ES el registro de
# auditoría de asignaciones (expuesto vía /leads/{id}/custodia/), y Lead se
# crea en lotes de miles de filas por carga masiva — auditar cada fila
# individual saturaría AuditLog sin aportar más que lo que ya registra
# LoteCarga (quién cargó qué archivo y cuándo).
audit_model(Category)
audit_model(SubCategory)
