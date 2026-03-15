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
    
    # Get or create profile - don't assume it exists
    profile, profile_created = UserProfile.objects.get_or_create(user=instance)
    
    # Check if this is a social user (Google) - they skip OTP
    # Social users have is_active=True set by adapter, regular users have is_active=False
    # Also check if email is already verified (Google users are pre-verified)
    if profile.email_verified:
        # Ensure user is active and skip OTP creation
        if not instance.is_active:
            instance.is_active = True
            instance.save(update_fields=['is_active'])
        return
    
    # For regular email signups: Mark user as inactive until verified
    if instance.is_active:
        instance.is_active = False
        instance.save(update_fields=['is_active'])
    
    # Create email verification code
    try:
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