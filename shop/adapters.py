from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.db import IntegrityError, transaction


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter - disables allauth email verification, uses OTP instead"""
    
    def is_open_for_signup(self, request):
        return True
    
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """SKIP allauth's confirmation email - we use OTP system instead"""
        pass


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter for Google OAuth - AUTO SIGNUP"""
    
    def is_open_for_signup(self, request, sociallogin):
        return True
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user after Google login.
        Google users are pre-verified, so we activate them immediately.
        """
        from .models import UserProfile
        from django.contrib.auth.models import User
        
        # Save user first using parent's save_user
        user = super().save_user(request, sociallogin, form)
        
        # Get Google data
        data = sociallogin.account.extra_data
        first_name = data.get('given_name', '')
        last_name = data.get('family_name', '')
        email = data.get('email', '')
        
        # Update user info from Google
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if email and not user.email:
            user.email = email
        
        # Activate immediately (Google users are pre-verified)
        user.is_active = True
        user.save()
        
        # Create/update profile with transaction to avoid race conditions
        try:
            with transaction.atomic():
                profile, created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'email_verified': True,
                        'is_fully_verified': True,
                    }
                )
                if not created:
                    profile.email_verified = True
                    profile.is_fully_verified = True
                    profile.save()
        except Exception as e:
            # Log error but don't crash - user is already saved
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Profile creation failed for {user.email}: {e}")
        
        return user
    
    def get_connect_redirect_url(self, request, socialaccount):
        return '/'
    
import logging

logger = logging.getLogger(__name__)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        logger.info(f"Google login attempt: {sociallogin.account.extra_data.get('email')}")
        
        try:
            user = super().save_user(request, sociallogin, form)
            logger.info(f"User saved: {user.username}, is_active: {user.is_active}")
        except Exception as e:
            logger.error(f"Google login error: {str(e)}")
            raise
        
        return user