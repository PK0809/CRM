# crm/apps.py
from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"

    def ready(self):
        """
        Import signals when the app is ready.
        This ensures Django connects them only once.
        """
        from . import signals  # noqa: F401
