from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.contrib import messages


class AdminNoCacheMiddleware:
    """Prevent caching of admin pages to avoid stale data"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Prevent caching for admin pages
        if request.path.startswith('/admin/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        return response


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


class VerificationRequiredMiddleware:
    """
    Middleware to require account verification for checkout and order placement.
    Only verified users can place orders.
    """
    
    VERIFICATION_REQUIRED_PATHS = [
        '/checkout/',
        '/payment/',
        '/order/',
    ]
    
    EXEMPT_PATHS = [
        '/login/',
        '/register/',
        '/verify-account/',
        '/resend-otp/',
        '/logout/',
        '/admin/',
        '/static/',
        '/media/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip exempt paths
        for path in self.EXEMPT_PATHS:
            if request.path.startswith(path):
                return self.get_response(request)
        
        # Check if path requires verification
        requires_verification = any(
            request.path.startswith(path) 
            for path in self.VERIFICATION_REQUIRED_PATHS
        )
        
        if requires_verification:
            try:
                profile = request.user.profile
                if not profile.is_fully_verified:
                    messages.warning(
                        request, 
                        'Please verify your email and phone number to complete this action.'
                    )
                    return redirect('profile')
            except:
                pass
        
        return self.get_response(request)


class MobileDetectionMiddleware:
    """
    Middleware to detect mobile devices and add flag to request.
    """
    
    MOBILE_USER_AGENTS = [
        'Mobile', 'Android', 'iPhone', 'iPad', 'iPod', 'Windows Phone',
        'BlackBerry', 'Opera Mini', 'IEMobile', ' Silk '
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        request.is_mobile = any(agent in user_agent for agent in self.MOBILE_USER_AGENTS)
        
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy (adjust as needed)
        csp = "default-src 'self'; "
        csp += "script-src 'self' 'unsafe-inline' https://js.stripe.com https://www.paypal.com; "
        csp += "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        csp += "font-src 'self' https://fonts.gstatic.com; "
        csp += "img-src 'self' data: https:; "
        csp += "connect-src 'self' https://api.stripe.com https://api.xendit.co https://api.paymongo.com; "
        csp += "frame-src https://js.stripe.com https://www.paypal.com;"
        
        response['Content-Security-Policy'] = csp
        
        return response
