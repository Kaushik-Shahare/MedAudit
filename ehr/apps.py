from django.apps import AppConfig


class EhrConfig(AppConfig):
    """AppConfig for the EHR app."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "ehr"
    
    def ready(self):
        """Import signals when the app is ready."""
        import ehr.signals
