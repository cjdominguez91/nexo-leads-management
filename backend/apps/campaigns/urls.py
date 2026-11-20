from rest_framework.routers import DefaultRouter

from .views import (
    CampaignFieldDefinitionViewSet,
    CampaignSectionViewSet,
    CampaignTypeViewSet,
    CampaignViewSet,
    LoteCargaViewSet,
)

router = DefaultRouter()
router.register("campaign-types", CampaignTypeViewSet, basename="campaign-type")
router.register("sections", CampaignSectionViewSet, basename="campaign-section")
router.register("field-definitions", CampaignFieldDefinitionViewSet, basename="field-definition")
router.register("campaigns", CampaignViewSet, basename="campaign")
router.register("lotes-carga", LoteCargaViewSet, basename="lote-carga")

urlpatterns = router.urls
