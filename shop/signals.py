from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from .models import UserProfile, Cart, VerificationCode
from .utils import send_email_otp


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile and cart when user is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        Cart.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


# NEW: Signal to create OTP token on user creation
@receiver(post_save, sender=User)
def create_verification_otp(sender, instance, created, **kwargs):
    """Create OTP verification code when user is created (if not a superuser or social user)"""
    if not created or instance.is_superuser:
        return
    
    # Check if this is a social login user by looking at the social account
    from allauth.socialaccount.models import SocialAccount
    
    # If user has a social account (Google, etc.), skip OTP and activate
    if SocialAccount.objects.filter(user=instance).exists():
        # Ensure profile exists and is marked verified
        profile, _ = UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'email_verified': True,
                'is_fully_verified': True,
            }
        )
        if not profile.email_verified:
            profile.email_verified = True
            profile.is_fully_verified = True
            profile.save()
        
        # Ensure user is active (they already should be from adapter, but double-check)
        if not instance.is_active:
            instance.is_active = True
            instance.save(update_fields=['is_active'])
        return
    
    # For regular email signups (no social account): Create OTP
    # Only deactivate if they're not already active
    if instance.is_active:
        instance.is_active = False
        instance.save(update_fields=['is_active'])
    
    try:
        # Get or create profile
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        
        # Create email verification code
        verification = VerificationCode.objects.create(
            user=instance,
            verification_type='email',
            email=instance.email,
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        )
        
        # Send OTP via email
        send_email_otp(instance, instance.email)
        
        # If phone is provided, create phone verification too
        if profile.phone:
            VerificationCode.objects.create(
                user=instance,
                verification_type='phone',
                phone=profile.phone,
                expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
            )
    except Exception as e:
        # Log error but don't crash user creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create verification OTP for {instance.email}: {e}")