# config/__init__.py
import copy
from django.template import context
from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'
    verbose_name = 'Shop'

    def ready(self):
        import shop.signals  # Import signals


original_copy = context.Context.__copy__

def patched_copy(self):
    try:
        return original_copy(self)
    except AttributeError:
        from django.template.context import Context
        return Context(dict=self.flatten())

context.Context.__copy__ = patched_copy
