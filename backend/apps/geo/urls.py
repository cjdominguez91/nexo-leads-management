from rest_framework.routers import DefaultRouter

from .views import AgenciaViewSet, TerritorioViewSet

router = DefaultRouter()
router.register("territorios", TerritorioViewSet, basename="territorio")
router.register("agencias", AgenciaViewSet, basename="agencia")

urlpatterns = router.urls
