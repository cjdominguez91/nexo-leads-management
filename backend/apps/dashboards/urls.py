from django.urls import path

from .views import EfectividadView, ResumenView, TendenciaView

urlpatterns = [
    path("resumen/", ResumenView.as_view(), name="dashboard-resumen"),
    path("tendencia/", TendenciaView.as_view(), name="dashboard-tendencia"),
    path("efectividad/", EfectividadView.as_view(), name="dashboard-efectividad"),
]
