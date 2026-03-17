"""
Django settings for config project.
Enhanced with PostgreSQL for Render, Payment Integration, SMS/Email OTP, 
Shipping System, and Google OAuth Sign-In.
"""
from pathlib import Path
import os
import dj_database_url
from decouple import config
from django.templatetags.static import static
from django.urls import reverse_lazy
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'
load_dotenv(env_path, override=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-%7_au68r_#c7b%n$#2$u^fr&7hb-dwvc7jw6ll+ak_64k#qu%1')

# SECURITY WARNING: don't run with debug turned on in production!
if config('DATABASE_URL', default=None):
    DEBUG = False
else:
    DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.inlines',
    'unfold.contrib.guardian',
    'unfold.contrib.simple_history',

    # Django core - AFTER Unfold
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'ckeditor',
    'ckeditor_uploader',
    'colorfield',
    'admin_interface',
    'cloudinary',
    'cloudinary_storage',
    'storages',

    # allauth apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Local apps
    'shop',
]

SITE_ID = 1  # Required for allauth

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
    # allauth middleware - MUST BE AFTER VerificationRequiredMiddleware
    'allauth.account.middleware.AccountMiddleware',
]

# Cache settings
CACHE_MIDDLEWARE_SECONDS = 0
CACHE_MIDDLEWARE_KEY_PREFIX = ''

ROOT_URLCONF = 'config.urls'

# =============================================================================
# TEMPLATES - FIXED FOR ALLAUTH
# =============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',  # ADD THIS for allauth templates
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # Required by allauth
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
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    # Use DATABASE_URL if provided
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Fallback to individual DB_* variables
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='malice_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
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
# STATIC & MEDIA FILES - FIXED FOR CLOUDINARY
# ============================================

# Static files (WhiteNoise for both local and production)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'shop', 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================
# CLOUDINARY CONFIGURATION - FIXED FOR RENDER
# ============================================
import cloudinary
import cloudinary_storage

CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = config('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = config('CLOUDINARY_API_SECRET', default='')

# Configure the cloudinary package
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

# ADD THIS - Required by django-cloudinary-storage
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
    'SECURE': True,
    'MEDIA_TAG': 'malice',
    'STATIC_TAG': 'malice-static',
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

MEDIA_URL = '/media/'

# =============================================================================
# DJANGO-ALLAUTH CONFIGURATION - GOOGLE SIGN-IN
# =============================================================================

# Authentication backends - REQUIRED
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# allauth Account Adapter
ACCOUNT_ADAPTER = 'shop.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'shop.adapters.CustomSocialAccountAdapter'

# Account settings
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'

# Social Account settings
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True  
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_STORE_TOKENS = False

# Google OAuth Provider Configuration
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID', default=''),
            'secret': config('GOOGLE_CLIENT_SECRET', default=''),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

# Redirect URLs
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'

# Social Auth Pipeline - Custom signup flow for phone verification
SOCIALACCOUNT_SIGNUP_FORM_CLASS = 'shop.forms.SocialSignupForm'

# Custom redirect after social login to collect phone number
SOCIALACCOUNT_LOGIN_ON_GET = True

# Security settings for OAuth
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# ============================================
# AUTHENTICATION & SESSION SETTINGS
# ============================================
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = 'malice_sessionid'
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

ADMIN_SESSION_COOKIE_NAME = 'malice_admin_sessionid'
FRONTEND_SESSION_COOKIE_NAME = 'malice_sessionid'


# ============================================
# EMAIL CONFIGURATION - RESEND SMTP (PORT 465)
# ============================================

IS_PRODUCTION = config('DATABASE_URL', default=None) is not None

if IS_PRODUCTION:
    # Production - Use Resend SMTP with SSL (port 465)
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.resend.com')
    EMAIL_PORT = config('EMAIL_PORT', default=465, cast=int)
    EMAIL_USE_SSL = True  # Required for port 465
    EMAIL_USE_TLS = False  # Don't use TLS with SSL
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='resend')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='onboarding@resend.dev')
    DEFAULT_FROM_NAME = config('DEFAULT_FROM_NAME', default='MALICE Store')

    print("="*50)
    print("EMAIL CONFIGURATION (RESEND SMTP - SSL)")
    print(f"EMAIL_HOST: {EMAIL_HOST}")
    print(f"EMAIL_PORT: {EMAIL_PORT}")
    print(f"EMAIL_USE_SSL: {EMAIL_USE_SSL}")
    print(f"DEFAULT_FROM_EMAIL: {DEFAULT_FROM_EMAIL}")
    print("="*50)

else:
    # Development - console only
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST = 'smtp.resend.com'
    EMAIL_PORT = 465
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
    EMAIL_HOST_USER = 'resend'
    EMAIL_HOST_PASSWORD = ''
    DEFAULT_FROM_EMAIL = 'onboarding@resend.dev'
    DEFAULT_FROM_NAME = 'MALICE Store'

# ============================================
# TWILIO SMS CONFIGURATION - FOR OTP
# ============================================
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')

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
# REDIS & CELERY CONFIGURATION - FIXED
# ============================================
REDIS_URL = config('REDIS_URL', default=None)

if DEBUG:
    # Development - use local memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = None
    CELERY_RESULT_BACKEND = None

elif REDIS_URL:
    # Production with Redis
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TASK_ALWAYS_EAGER = False

else:
    # Production fallback to database cache (no Redis needed)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache_table',
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_BROKER_URL = None
    CELERY_RESULT_BACKEND = None

# Celery settings
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
                    {"title": "Orders", "icon": "shopping_cart", "link": "/admin/shop/order/"},
                    {"title": "Payments", "icon": "payment", "link": "/admin/shop/payment/"},
                    {"title": "Shipping Methods", "icon": "local_shipping", "link": "/admin/shop/shippingmethod/"},
                    {"title": "Shipping Rates", "icon": "attach_money", "link": "/admin/shop/shippingrate/"},
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

# ============================================
# LOGGING
# ============================================
import logging
import sys

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ============================================
# CKEDITOR CONFIGURATION
# ============================================
CKEDITOR_UPLOAD_PATH = 'uploads/ckeditor/'

# Optional: Additional CKEDITOR settings
CKEDITOR_IMAGE_BACKEND = 'pillow'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
    },
}

# ============================================
# ALLAUTH GOOGLE OAUTH - REDIRECT URI FIX
# ============================================

# Force the callback URL to use the correct path
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if not DEBUG else 'http'

# Add this to ensure redirect URI matches exactly
SOCIALACCOUNT_CALLBACK_URLS = {
    'google': '/accounts/google/login/callback/'
}