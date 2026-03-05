# config/__init__.py
import copy
from django.template import context

# Save original __copy__ method
_original_context_copy = context.Context.__copy__

def _patched_context_copy(self):
    """
    Patched __copy__ for Django's Context class to work with Python 3.14+
    """
    from django.template.context import Context
    new_context = Context.__new__(Context)
    
    # Copy all the attributes manually
    new_context.dicts = self.dicts[:]
    if hasattr(self, 'autoescape'):
        new_context.autoescape = self.autoescape
    if hasattr(self, 'use_l10n'):
        new_context.use_l10n = self.use_l10n
    if hasattr(self, 'use_tz'):
        new_context.use_tz = self.use_tz
    if hasattr(self, 'current_app'):
        new_context.current_app = self.current_app
    if hasattr(self, 'request'):
        new_context.request = self.request
    
    return new_context

# Apply the patch
context.Context.__copy__ = _patched_context_copy

# Also patch BaseContext if needed
if hasattr(context.BaseContext, '__copy__'):
    def _patched_base_copy(self):
        from django.template.context import BaseContext
        new_context = BaseContext.__new__(BaseContext)
        new_context.dicts = self.dicts[:]
        return new_context
    
    context.BaseContext.__copy__ = _patched_base_copy