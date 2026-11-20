from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, LeadViewSet, SubCategoryViewSet, UsuariosAsignablesViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("subcategories", SubCategoryViewSet, basename="subcategory")
router.register("leads", LeadViewSet, basename="lead")
router.register("usuarios-asignables", UsuariosAsignablesViewSet, basename="usuario-asignable")

urlpatterns = router.urls
