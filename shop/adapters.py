from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.db import IntegrityError, transaction
import logging

logger = logging.getLogger(__name__)


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
    
    def pre_social_login(self, request, sociallogin):
        """Called before the social login process"""
        logger.info(f"Pre-social login: {sociallogin.account.provider}")
        return super().pre_social_login(request, sociallogin)
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user after Google login.
        Google users are pre-verified, so we activate them immediately.
        """
        from .models import UserProfile
        
        logger.info(f"Saving social user: {sociallogin.account.extra_data.get('email')}")
        
        try:
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
            
            # CRITICAL: Activate immediately (Google users are pre-verified)
            user.is_active = True
            user.save()
            
            logger.info(f"User saved successfully: {user.username}, is_active: {user.is_active}")
            
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
                logger.error(f"Profile creation failed for {user.email}: {e}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error saving social user: {str(e)}")
            raise
    
    def get_connect_redirect_url(self, request, socialaccount):
        return '/'