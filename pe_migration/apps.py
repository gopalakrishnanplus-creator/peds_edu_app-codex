from django.apps import AppConfig


class PeMigrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pe_migration"
    verbose_name = "PE source migration v2"
