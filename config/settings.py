"""
Django settings for config project.
Enhanced with PostgreSQL for Render, Payment Integration, SMS/Email OTP, and Shipping System.
"""

from pathlib import Path
import os
import dj_database_url
from decouple import config, Csv
from django.templatetags.static import static
from django.urls import reverse_lazy

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-%7_au68r_#c7b%n$#2$u^fr&7hb-dwvc7jw6ll+ak_64k#qu%1')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# Application definition
INSTALLED_APPS = [
    "unfold",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'shop',
]

# Middleware
MIDDLEWARE = [
    'shop.middleware.AdminNoCacheMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'shop.middleware.SeparateAdminSessionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'shop.middleware.VerificationRequiredMiddleware',
]

# Cache settings
CACHE_MIDDLEWARE_SECONDS = 0
CACHE_MIDDLEWARE_KEY_PREFIX = ''

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shop.context_processors.cart_context',
                'shop.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ============================================
# DATABASE CONFIGURATION - FIXED FOR RENDER
# ============================================
# Priority: 1. DATABASE_URL (Render PostgreSQL), 2. Local PostgreSQL, 3. SQLite (fallback)
# ============================================
# DATABASE CONFIGURATION - RENDER + LOCAL DEV
# ============================================
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    # Production: Render PostgreSQL
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Local Development: SQLite (no PostgreSQL server needed)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

# ============================================
# STATIC & MEDIA FILES
# ============================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'shop', 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================
# AUTHENTICATION & SESSION SETTINGS
# ============================================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = 'malice_sessionid'
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

ADMIN_SESSION_COOKIE_NAME = 'malice_admin_sessionid'
FRONTEND_SESSION_COOKIE_NAME = 'malice_sessionid'

# ============================================
# EMAIL CONFIGURATION - FOR OTP & NOTIFICATIONS
# ============================================
if DEBUG:
    # Development - print emails to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Production - Plunk SMTP
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'next-smtp.useplunk.com'
    EMAIL_PORT = 2587  # STARTTLS port
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'plunk'  # Username is always 'plunk'
    EMAIL_HOST_PASSWORD = config('PLUNK_SMTP_PASSWORD')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@malice.com')

# ============================================
# TWILIO SMS CONFIGURATION - FOR OTP
# ============================================
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')
TWILIO_WHATSAPP_NUMBER = config('TWILIO_WHATSAPP_NUMBER', default='')

# ============================================
# PAYMENT GATEWAY CONFIGURATIONS
# ============================================

# Stripe (for Credit/Debit Cards)
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

# PayPal
PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_MODE = config('PAYPAL_MODE', default='sandbox')  # sandbox or live

# GCash (via Xendit or PayMongo)
XENDIT_SECRET_KEY = config('XENDIT_SECRET_KEY', default='')
XENDIT_PUBLIC_KEY = config('XENDIT_PUBLIC_KEY', default='')
XENDIT_WEBHOOK_TOKEN = config('XENDIT_WEBHOOK_TOKEN', default='')

# PayMongo
PAYMONGO_SECRET_KEY = config('PAYMONGO_SECRET_KEY', default='')
PAYMONGO_PUBLIC_KEY = config('PAYMONGO_PUBLIC_KEY', default='')
PAYMONGO_WEBHOOK_SECRET = config('PAYMONGO_WEBHOOK_SECRET', default='')

# Maya (via PayMaya)
MAYA_PUBLIC_API_KEY = config('MAYA_PUBLIC_API_KEY', default='')
MAYA_SECRET_API_KEY = config('MAYA_SECRET_API_KEY', default='')
MAYA_WEBHOOK_SECRET = config('MAYA_WEBHOOK_SECRET', default='')

# ============================================
# REDIS & CELERY CONFIGURATION
# ============================================
# ============================================
# REDIS & CELERY CONFIGURATION
# ============================================
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# Only use Redis in production, use local memory cache in development
if DEBUG:
    # Development - use local memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    
    # Disable Celery in development (or use synchronous tasks)
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    # Production - use Redis
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }

# Celery Configuration - only used if Redis is available
CELERY_BROKER_URL = REDIS_URL if not DEBUG else None
CELERY_RESULT_BACKEND = REDIS_URL if not DEBUG else None
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ============================================
# OTP SETTINGS
# ============================================
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 6
MAX_OTP_ATTEMPTS = 3
MAX_OTP_RESEND = 3

# ============================================
# PROMOTION SETTINGS
# ============================================
FREE_SHIPPING_THRESHOLD = 3000  # Orders above this get free shipping
NEW_USER_FREE_SHIPPING = True   # First order free shipping for verified users
WELCOME_DISCOUNT_PERCENT = 10   # Welcome discount percentage

# ============================================
# SHIPPING SETTINGS
# ============================================
DEFAULT_SHIPPING_COST = 150
EXPRESS_SHIPPING_COST = 350
SAME_DAY_SHIPPING_COST = 500
INTERNATIONAL_SHIPPING_COST = 800

# ============================================
# MESSAGES
# ============================================
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# ============================================
# UNFOLD ADMIN CONFIGURATION
# ============================================
UNFOLD = {
    "SITE_TITLE": "MALICE Admin",
    "SITE_HEADER": "MALICE Administration",
    "SITE_SUBHEADER": "E-Commerce Management",
    "SITE_DROPDOWN": [
        {"icon": "person", "title": "View Site", "link": "/"},
    ],
    "SITE_SYMBOL": "shopping_bag",
    "DARK_MODE": True,
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Shop Management",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Products", "icon": "inventory_2", "link": "/admin/shop/product/"},
                    {"title": "Categories", "icon": "category", "link": "/admin/shop/category/"},
                    {"title": "Product Variants", "icon": "format_size", "link": "/admin/shop/productvariant/"},
                ],
            },
            {
                "title": "Orders & Customers",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Orders", "icon": "shopping_cart", "link": reverse_lazy("admin:shop_order_changelist")},
                    {"title": "Payments", "icon": "payment", "link": reverse_lazy("admin:shop_payment_changelist")},
                    {"title": "Shipping Methods", "icon": "local_shipping", "link": reverse_lazy("admin:shop_shippingmethod_changelist")},
                    {"title": "Shipping Rates", "icon": "attach_money", "link": reverse_lazy("admin:shop_shippingrate_changelist")},
                ],
            },
            {
                "title": "User Management",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "Users", "icon": "people", "link": reverse_lazy("admin:auth_user_changelist")},
                    {"title": "User Profiles", "icon": "person", "link": reverse_lazy("admin:shop_userprofile_changelist")},
                    {"title": "Verification Codes", "icon": "verified", "link": reverse_lazy("admin:shop_verificationcode_changelist")},
                ],
            },
        ],
    },
    
    "COLORS": {
        "primary": {
            "50": "#fafafa", "100": "#f5f5f5", "200": "#e5e5e5",
            "300": "#d4d4d4", "400": "#a3a3a3", "500": "#737373",
            "600": "#525252", "700": "#404040", "800": "#262626",
            "900": "#171717", "950": "#0a0a0a",
        },
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
