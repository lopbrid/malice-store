from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.deprecation import MiddlewareMixin

class SeparateAdminSessionMiddleware(MiddlewareMixin):
    """
    Middleware to separate admin sessions from frontend sessions.
    This prevents admin login from auto-logging into customer frontend.
    """
    
    def process_request(self, request):
        # Determine if this is an admin request
        is_admin_path = request.path.startswith('/admin/')
        
        # Store the original cookie name
        self.original_cookie_name = settings.SESSION_COOKIE_NAME
        
        # Use different cookie names for admin vs frontend
        if is_admin_path:
            # Admin uses the default or admin-specific cookie
            settings.SESSION_COOKIE_NAME = getattr(settings, 'ADMIN_SESSION_COOKIE_NAME', 'malice_admin_sessionid')
        else:
            # Frontend uses frontend-specific cookie
            settings.SESSION_COOKIE_NAME = getattr(settings, 'FRONTEND_SESSION_COOKIE_NAME', 'malice_sessionid')
    
    def process_response(self, request, response):
        # Restore original cookie name to prevent side effects
        settings.SESSION_COOKIE_NAME = self.original_cookie_name
        return response