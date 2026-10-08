"""`registry` ilovasi konfiguratsiyasi."""
from django.apps import AppConfig


class RegistryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.registry"
    label = "registry"
    verbose_name = "Reyestr"

    def ready(self) -> None:
        from . import signals  # noqa: F401 — signal qabul qiluvchilarni ulash
