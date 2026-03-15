from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


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
        
        # Save user first
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
        
        # Create/update profile - mark as fully verified
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.email_verified = True
        profile.is_fully_verified = True
        profile.save()
        
        return user
    
    def get_connect_redirect_url(self, request, socialaccount):
        return '/'