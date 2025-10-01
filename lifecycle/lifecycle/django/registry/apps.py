from django.apps import AppConfig


class RegistryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lifecycle.django.registry'

    def ready(self):
        # Needed to connect signals to receivers
        import lifecycle.django.registry.signals  # noqa: F401
