# formacion/apps.py
from django.apps import AppConfig


class FormacionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'formacion'

    def ready(self):
        pass
    