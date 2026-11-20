from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/geo/", include("apps.geo.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/campaigns/", include("apps.campaigns.urls")),
    path("api/leads/", include("apps.leads.urls")),
    path("api/opportunities/", include("apps.opportunities.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/dashboards/", include("apps.dashboards.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
