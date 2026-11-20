from apps.audit.signals import audit_model

from .models import Campaign, CampaignFieldDefinition, CampaignType, LoteCarga

audit_model(CampaignType)
audit_model(CampaignFieldDefinition)
audit_model(Campaign)
audit_model(LoteCarga)
