# signals.py - FIXED
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from .models import UserProfile, Cart, VerificationCode
from .utils import send_email_otp
from allauth.socialaccount.models import SocialAccount
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def handle_user_created(sender, instance, created, **kwargs):
    """Handle user creation: profile, cart, and OTP verification"""
    if not created:
        return
    
    # Create profile and cart for ALL users
    UserProfile.objects.get_or_create(user=instance)
    Cart.objects.get_or_create(user=instance)
    
    # Skip OTP for superusers and social auth users
    if instance.is_superuser:
        return
        
    # Check if social auth user (Google login)
    if SocialAccount.objects.filter(user=instance).exists():
        # Activate immediately, mark as verified
        profile = instance.profile
        profile.email_verified = True
        profile.is_fully_verified = True
        profile.save()
        
        if not instance.is_active:
            instance.is_active = True
            instance.save(update_fields=['is_active'])
        return
    
    # Regular email signup: deactivate and send OTP
    if instance.is_active:
        instance.is_active = False
        instance.save(update_fields=['is_active'])
    
    try:
        # Create verification code
        verification = VerificationCode.objects.create(
            user=instance,
            verification_type='email',
            email=instance.email,
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        )
        
        # Send OTP email
        success = send_email_otp(instance, instance.email)
        
        if success:
            logger.info(f"✅ OTP sent successfully to {instance.email}")
        else:
            logger.error(f"❌ Failed to send OTP to {instance.email}")
            
    except Exception as e:
        logger.error(f"Failed to create/send OTP for {instance.email}: {e}")