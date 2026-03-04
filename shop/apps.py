# config/__init__.py
import copy
from django.template import context

original_copy = context.Context.__copy__

def patched_copy(self):
    try:
        return original_copy(self)
    except AttributeError:
        from django.template.context import Context
        return Context(dict=self.flatten())

context.Context.__copy__ = patched_copy
