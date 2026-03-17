import random
import string
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import stripe
from twilio.rest import Client
import logging
import json

logger = logging.getLogger(__name__)


def generate_otp(length=6):
    """Generate a random numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


# ============================================
# OTP UTILITIES - RESEND SMTP (using Django send_mail)
# ============================================

def send_email_otp(user, email):
    """Send OTP via Resend SMTP using Django's built-in send_mail"""
    from .models import VerificationCode

    try:
        # Generate OTP
        otp = generate_otp()

        # Invalidate old codes
        VerificationCode.objects.filter(
            user=user,
            verification_type='email',
            is_used=False
        ).update(is_used=True)

        # Create new verification record
        verification = VerificationCode.objects.create(
            user=user,
            code=otp,
            verification_type='email',
            email=email,
            expires_at=timezone.now() + timezone.timedelta(minutes=10)
        )

        # HTML email template
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #000; color: #fff; padding: 20px; text-align: center; }}
        .content {{ padding: 30px; background: #f9f9f9; }}
        .code {{ font-size: 32px; font-weight: bold; color: #000; letter-spacing: 5px; 
                padding: 20px; background: #fff; border: 2px solid #000; 
                text-align: center; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MALICE</h1>
        </div>
        <div class="content">
            <h2>Hello {user.first_name or user.username},</h2>
            <p>Thank you for registering with MALICE!</p>
            <p>Your verification code is:</p>
            <div class="code">{otp}</div>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>© 2024 MALICE. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

        # Plain text version
        text_content = f"""Hello {user.first_name or user.username},

Thank you for registering with MALICE!

Your verification code is: {otp}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
The MALICE Team
"""

        # Send email via Django's send_mail (uses Resend SMTP settings from settings.py)
        sent = send_mail(
            subject='MALICE - Your Verification Code',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_content,
            fail_silently=False,
        )

        if sent:
            logger.info(f"✅ OTP sent successfully via Resend SMTP to {email}")
            return True
        else:
            logger.error(f"❌ Failed to send OTP to {email}")
            verification.delete()
            return False

    except Exception as e:
        logger.error(f"❌ Email sending failed: {e}")
        # Clean up verification code on failure
        try:
            verification.delete()
        except:
            pass
        return False


def send_sms_otp(user, phone_number):
    """Send OTP via SMS using Twilio"""
    from .models import VerificationCode

    # Generate OTP
    otp = generate_otp()

    # Invalidate old unused codes
    VerificationCode.objects.filter(
        user=user,
        verification_type='phone',
        is_used=False
    ).update(is_used=True)

    # Create verification record
    VerificationCode.objects.create(
        user=user,
        code=otp,
        verification_type='phone',
        phone=phone_number,
        expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    )

    # Check if Twilio is configured
    if not hasattr(settings, 'TWILIO_ACCOUNT_SID') or not settings.TWILIO_ACCOUNT_SID:
        # In development, just print to console
        if settings.DEBUG:
            print(f"\n{{'='*50}}")
            print(f"📱 SMS VERIFICATION CODE for {phone_number}: {otp}")
            print(f"(Twilio not configured - this would be sent via SMS)")
            print(f"{{'='*50}}\n")
            return True
        return False

    # In production with Twilio configured
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Send SMS
        message = client.messages.create(
            body=f'Your MALICE verification code is: {otp}. Valid for {settings.OTP_EXPIRY_MINUTES} minutes.',
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        logger.info(f"SMS sent to {phone_number}")
        return True
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        return False

# ============================================
# SHIPPING CALCULATIONS
# ============================================

def calculate_shipping_cost(method, weight_kg, subtotal, region=None, user=None):
    """
    Calculate shipping cost based on method, weight, subtotal, and region
    Also checks for free shipping promotions
    """
    from .models import ShippingRate

    # Check for free shipping threshold
    if subtotal >= settings.FREE_SHIPPING_THRESHOLD:
        return 0

    # Check for new user free shipping promotion
    if user and settings.NEW_USER_FREE_SHIPPING:
        profile = user.profile
        if not profile.first_order_completed and profile.is_fully_verified:
            return 0

    # Get applicable shipping rate
    rate = ShippingRate.objects.filter(
        shipping_method=method,
        weight_min__lte=weight_kg,
        weight_max__gte=weight_kg,
        is_active=True
    ).first()

    if rate:
        # Check region-specific rate
        if region:
            region_rate = ShippingRate.objects.filter(
                shipping_method=method,
                region__name__iexact=region,
                weight_min__lte=weight_kg,
                weight_max__gte=weight_kg,
                is_active=True
            ).first()
            if region_rate:
                return region_rate.calculate_cost(weight_kg, subtotal)

        return rate.calculate_cost(weight_kg, subtotal)

    # Fallback to default rates
    if method.method_type == 'standard':
        return 0 if subtotal >= 3000 else 150
    elif method.method_type == 'express':
        return 350
    elif method.method_type == 'same_day':
        return 500
    elif method.method_type == 'international':
        return 800

    return 150


def get_shipping_estimate(destination, weight_kg, method_type='standard'):
    """Get shipping estimate for a destination"""
    from .models import ShippingMethod, ShippingRegion, ShippingRate

    method = ShippingMethod.objects.filter(method_type=method_type, is_active=True).first()
    if not method:
        return None

    region = ShippingRegion.objects.filter(name__iexact=destination, is_active=True).first()

    rate = ShippingRate.objects.filter(
        shipping_method=method,
        region=region,
        weight_min__lte=weight_kg,
        weight_max__gte=weight_kg,
        is_active=True
    ).first()

    if rate:
        return {
            'cost': float(rate.base_cost),
            'cost_per_kg': float(rate.cost_per_kg),
            'estimated_days': f"{method.estimated_days_min}-{method.estimated_days_max}",
            'method': method.name
        }

    return None


# ============================================
# PAYMENT PROCESSING
# ============================================

def create_payment_intent(order):
    """Create Stripe PaymentIntent"""
    stripe.api_key = settings.STRIPE_SECRET_KEY

    intent = stripe.PaymentIntent.create(
        amount=int(order.total * 100),
        currency='php',
        metadata={
            'order_number': order.order_number,
            'user_id': order.user.id,
        },
        automatic_payment_methods={'enabled': True},
    )

    return intent


def process_stripe_payment(payment, payment_intent_id):
    """Process Stripe payment"""
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        if intent.status == 'succeeded':
            payment.mark_completed(intent.id)
            return {'success': True}
        elif intent.status == 'requires_action':
            return {
                'success': False,
                'requires_action': True,
                'client_secret': intent.client_secret
            }
        else:
            return {'success': False, 'error': f'Payment status: {intent.status}'}

    except stripe.error.CardError as e:
        return {'success': False, 'error': e.user_message}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def process_gcash_payment(payment, data):
    """Process GCash payment via Xendit or PayMongo"""
    try:
        if settings.XENDIT_SECRET_KEY:
            return _process_gcash_xendit(payment, data)
        elif settings.PAYMONGO_SECRET_KEY:
            return _process_gcash_paymongo(payment, data)
        return {'success': False, 'error': 'GCash payment gateway not configured'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _process_gcash_xendit(payment, data):
    """Process GCash via Xendit"""
    url = 'https://api.xendit.co/ewallets/charges'

    payload = {
        'reference_id': payment.order.order_number,
        'currency': 'PHP',
        'amount': float(payment.amount),
        'checkout_method': 'ONE_TIME_PAYMENT',
        'channel_code': 'PH_GCASH',
        'channel_properties': {
            'success_redirect_url': f'{settings.ALLOWED_HOSTS[0]}/order/confirmation/{payment.order.order_number}/',
            'failure_redirect_url': f'{settings.ALLOWED_HOSTS[0]}/payment/failed/{payment.order.order_number}/',
        }
    }

    response = requests.post(
        url,
        json=payload,
        auth=(settings.XENDIT_SECRET_KEY, ''),
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        result = response.json()
        payment.gateway_reference = result.get('id')
        payment.authentication_url = result.get('actions', {}).get('desktop_web_checkout_url', '')
        payment.save()
        return {'success': True, 'redirect_url': payment.authentication_url}

    return {'success': False, 'error': 'Failed to create GCash charge'}


def _process_gcash_paymongo(payment, data):
    """Process GCash via PayMongo"""
    url = 'https://api.paymongo.com/v1/sources'

    payload = {
        'data': {
            'attributes': {
                'type': 'gcash',
                'amount': int(payment.amount * 100),
                'currency': 'PHP',
                'redirect': {
                    'success': f'{settings.ALLOWED_HOSTS[0]}/order/confirmation/{payment.order.order_number}/',
                    'failed': f'{settings.ALLOWED_HOSTS[0]}/payment/failed/{payment.order.order_number}/',
                }
            }
        }
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            'Authorization': f'Basic {settings.PAYMONGO_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
    )

    if response.status_code == 200:
        result = response.json()
        source = result.get('data', {})
        payment.gateway_reference = source.get('id')
        payment.authentication_url = source.get('attributes', {}).get('redirect', {}).get('checkout_url', '')
        payment.save()
        return {'success': True, 'redirect_url': payment.authentication_url}

    return {'success': False, 'error': 'Failed to create GCash source'}


def process_maya_payment(payment, data):
    """Process Maya payment"""
    try:
        if not settings.MAYA_SECRET_API_KEY:
            return {'success': False, 'error': 'Maya payment gateway not configured'}

        url = 'https://pg-sandbox.paymaya.com/checkout/v1/checkouts'

        payload = {
            'totalAmount': {
                'currency': 'PHP',
                'value': float(payment.amount)
            },
            'requestReferenceNumber': payment.order.order_number,
            'redirectUrl': {
                'success': f'{settings.ALLOWED_HOSTS[0]}/order/confirmation/{payment.order.order_number}/',
                'failure': f'{settings.ALLOWED_HOSTS[0]}/payment/failed/{payment.order.order_number}/',
                'cancel': f'{settings.ALLOWED_HOSTS[0]}/payment/cancelled/{payment.order.order_number}/'
            }
        }

        response = requests.post(
            url,
            json=payload,
            headers={
                'Authorization': f'Basic {settings.MAYA_SECRET_API_KEY}',
                'Content-Type': 'application/json'
            }
        )

        if response.status_code == 200:
            result = response.json()
            payment.gateway_reference = result.get('checkoutId')
            payment.authentication_url = result.get('redirectUrl')
            payment.save()
            return {'success': True, 'redirect_url': payment.authentication_url}

        return {'success': False, 'error': 'Failed to create Maya checkout'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def process_paypal_payment(payment, data):
    """Process PayPal payment"""
    try:
        import paypalrestsdk

        paypalrestsdk.configure({
            'mode': settings.PAYPAL_MODE,
            'client_id': settings.PAYPAL_CLIENT_ID,
            'client_secret': settings.PAYPAL_CLIENT_SECRET
        })

        paypal_payment = paypalrestsdk.Payment({
            'intent': 'sale',
            'payer': {'payment_method': 'paypal'},
            'redirect_urls': {
                'return_url': f'{settings.ALLOWED_HOSTS[0]}/payment/paypal/execute/',
                'cancel_url': f'{settings.ALLOWED_HOSTS[0]}/payment/paypal/cancel/'
            },
            'transactions': [{
                'amount': {
                    'total': str(payment.amount),
                    'currency': 'PHP'
                },
                'description': f'Order {payment.order.order_number}'
            }]
        })

        if paypal_payment.create():
            payment.gateway_reference = paypal_payment.id
            payment.save()
            for link in paypal_payment.links:
                if link.method == 'REDIRECT':
                    return {'success': True, 'redirect_url': link.href}

        return {'success': False, 'error': 'Failed to create PayPal payment'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def verify_webhook_signature(payload, signature, secret):
    """Verify webhook signature"""
    import hmac
    import hashlib

    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


# ============================================
# PROMOTION UTILITIES
# ============================================

def apply_promotion_code(user, code, order_amount):
    """Apply promotion code and return discount amount"""
    from .models import Promotion

    try:
        promotion = Promotion.objects.get(code=code.upper(), is_active=True)
        valid, message = promotion.is_valid(user, order_amount)

        if valid:
            discount = promotion.calculate_discount(order_amount)
            return {'success': True, 'discount': discount, 'promotion': promotion}
        else:
            return {'success': False, 'error': message}

    except Promotion.DoesNotExist:
        return {'success': False, 'error': 'Invalid promotion code'}


def get_available_promotions(user, order_amount):
    """Get list of available promotions for user"""
    from .models import Promotion

    promotions = Promotion.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    )

    available = []
    for promo in promotions:
        valid, _ = promo.is_valid(user, order_amount)
        if valid:
            available.append(promo)

    return available