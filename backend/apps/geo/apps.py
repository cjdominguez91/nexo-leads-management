from django.apps import AppConfig


class GeoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.geo"
    verbose_name = "Territorios y Agencias"

    def ready(self):
        import apps.geo.signals  # noqa: F401
