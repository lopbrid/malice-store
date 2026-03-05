# config/__init__.py
"""
Python 3.14 compatibility patch for Django 4.2 template Context.

Python 3.14 changed how super() works with __copy__, causing Django's
Context.__copy__ to fail. This patch provides a proper __copy__ implementation.
"""

import copy
from django.template import context

# Store the original __copy__ method
_original_context_copy = context.Context.__copy__
_original_basecontext_copy = context.BaseContext.__copy__

def _patched_basecontext_copy(self):
    """
    Patched __copy__ for BaseContext that works with Python 3.14+
    """
    # Create new instance using __new__ to avoid __init__
    new_context = self.__class__.__new__(self.__class__)
    
    # Copy the dicts list (shallow copy of the list itself)
    new_context.dicts = self.dicts[:]
    
    return new_context

def _patched_context_copy(self):
    """
    Patched __copy__ for Context that works with Python 3.14+
    """
    # First, copy as BaseContext (gets dicts)
    new_context = _patched_basecontext_copy(self)
    
    # Copy all the additional Context-specific attributes
    new_context.autoescape = self.autoescape
    new_context.use_l10n = self.use_l10n
    new_context.use_tz = self.use_tz
    
    # render_context is CRITICAL - it holds state during template rendering
    from django.template.context import RenderContext
    new_context.render_context = RenderContext()
    
    # Copy other attributes if present
    if hasattr(self, 'template'):
        new_context.template = self.template
    if hasattr(self, '_processors'):
        new_context._processors = self._processors
    if hasattr(self, '_processors_index'):
        new_context._processors_index = self._processors_index
    if hasattr(self, 'request'):
        new_context.request = self.request
    if hasattr(self, '_request'):
        new_context._request = self._request
    if hasattr(self, 'current_app'):
        new_context.current_app = self.current_app
    
    return new_context

# Apply the patches
context.BaseContext.__copy__ = _patched_basecontext_copy
context.Context.__copy__ = _patched_context_copy

# Also patch RequestContext if it exists
if hasattr(context, 'RequestContext'):
    def _patched_requestcontext_copy(self):
        new_context = _patched_context_copy(self)
        new_context.__class__ = context.RequestContext
        if hasattr(self, '_processors'):
            new_context._processors = self._processors
        if hasattr(self, '_processors_index'):
            new_context._processors_index = self._processors_index
        return new_context
    
    context.RequestContext.__copy__ = _patched_requestcontext_copy