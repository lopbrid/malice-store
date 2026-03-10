from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Cart
from django.conf import settings
from django.utils import timezone
from .models import UserProfile, Cart, VerificationCode
from .utils import send_email_otp



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile and cart when user is created"""
    if created:
        UserProfile.objects.create(user=instance)
        Cart.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


# NEW: Signal to create OTP token on user creation
@receiver(post_save, sender=User)
def create_verification_otp(sender, instance, created, **kwargs):
    """Create OTP verification code when user is created (if not a superuser)"""
    if created and not instance.is_superuser:
        # Mark user as inactive until verified
        instance.is_active = False
        instance.save()
        
        # Create email verification code
        VerificationCode.objects.create(
            user=instance,
            verification_type='email',
            email=instance.email,
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        )
        
        # Send OTP via email
        send_email_otp(instance, instance.email)
        
        # If phone is provided, create phone verification too
        profile = instance.profile
        if profile.phone:
            VerificationCode.objects.create(
                user=instance,
                verification_type='phone',
                phone=profile.phone,
                expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
            )
