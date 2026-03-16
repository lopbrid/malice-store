from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User  # ← MOVE HERE
from django.urls import reverse  # ← MOVE HERE
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
import json
import stripe
import random
import logging
from django.http import HttpResponse
from .utils import send_email_otp
from django.contrib.auth.models import User

def test_email(request):
    user = User.objects.first()
    
    if not user:
        return HttpResponse("No users found")

    success = send_email_otp(user, user.email)

    if success:
        return HttpResponse("✅ Email Sent!")
    else:
        return HttpResponse("❌ Email failed")

logger = logging.getLogger(__name__)


def test_email_render(request):
    from django.conf import settings
    import os
    
    # Collect debug info
    debug_info = {
        'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        'EMAIL_HOST': settings.EMAIL_HOST,
        'EMAIL_PORT': settings.EMAIL_PORT,
        'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
        'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
        'PLUNK_SMTP_PASSWORD set': 'PLUNK_SMTP_PASSWORD' in os.environ,
        'DEFAULT_FROM_EMAIL env': os.environ.get('DEFAULT_FROM_EMAIL', 'NOT SET'),
    }
    
    try:
        sent = send_mail(
            'Test from Render',
            f'This is a test from your Render deployment.\n\nDebug info:\n{debug_info}',
            settings.DEFAULT_FROM_EMAIL,
            ['namosgi519@gmail.com'],
            fail_silently=False,
        )
        if sent:
            return HttpResponse(f"""
                <h1>✅ Email Sent!</h1>
                <p>From: {settings.DEFAULT_FROM_EMAIL}</p>
                <h2>Debug Info:</h2>
                <pre>{debug_info}</pre>
            """)
        else:
            return HttpResponse("❌ Email failed to send")
    except Exception as e:
        return HttpResponse(f"""
            <h1>❌ Error</h1>
            <p>{str(e)}</p>
            <h2>Debug Info:</h2>
            <pre>{debug_info}</pre>
        """)

from .models import (
    Product, Category, ProductVariant, Cart, CartItem,
    Wishlist, Order, OrderItem, UserProfile, VerificationCode,
    ShippingMethod, ShippingRate, ShippingRegion, Payment,
    PaymentWebhookLog, Promotion, UserPromotionUse
)
from .forms import (
    CustomAuthenticationForm, CustomUserCreationForm,
    CheckoutForm, UserProfileForm, PasswordChangeForm,
    OTPVerificationForm, ResendOTPForm, CardPaymentForm,
    GCashPaymentForm, MayaPaymentForm, ForgotPasswordForm,
    ResetPasswordForm, UserRegisterForm
)
from .utils import (
    send_sms_otp, send_email_otp, calculate_shipping_cost,
    process_stripe_payment, process_gcash_payment, process_maya_payment,
    process_paypal_payment, create_payment_intent, verify_webhook_signature
)


# ============================================
# HOME & PRODUCT VIEWS
# ============================================

def home(request):
    """Home page view"""
    featured_products = Product.objects.filter(
        is_active=True, is_featured=True
    ).select_related('category').prefetch_related('variants')[:6]
    
    new_arrivals = Product.objects.filter(
        is_active=True, is_new=True
    ).select_related('category').prefetch_related('variants')[:4]
    
    best_sellers = Product.objects.filter(
        is_active=True, is_best_seller=True
    ).select_related('category').prefetch_related('variants')[:4]
    
    # Get user's wishlist product IDs if authenticated - FIXED
    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True))
    
    # Add in_wishlist flag to products - CONVERT TO LISTS FIRST
    featured_list = list(featured_products)
    new_list = list(new_arrivals)
    best_list = list(best_sellers)
    
    for product in featured_list:
        product.in_wishlist = product.id in user_wishlist_ids
    for product in new_list:
        product.in_wishlist = product.id in user_wishlist_ids
    for product in best_list:
        product.in_wishlist = product.id in user_wishlist_ids
    
    context = {
        'featured': featured_list,
        'new_arrivals': new_list,
        'best_sellers': best_list,
    }
    return render(request, 'shop/home.html', context)


def product_list(request):
    """Product list view with filtering and sorting"""
    products = Product.objects.filter(is_active=True).prefetch_related('variants')
    
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    sort_by = request.GET.get('sort', 'newest')
    
    if category_slug:
        if category_slug == 'new':
            products = products.filter(is_new=True)
        elif category_slug == 'best':
            products = products.filter(is_best_seller=True)
        else:
            products = products.filter(category__slug=category_slug)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    if sort_by == 'price-low':
        products = products.order_by('price')
    elif sort_by == 'price-high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')
    
    # Get user's wishlist product IDs - FIXED VERSION
    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True))
    
    # Add in_wishlist flag to products - CONVERT TO LIST FIRST
    product_list = list(products)  # Convert QuerySet to list
    for product in product_list:
        product.in_wishlist = product.id in user_wishlist_ids
    
    paginator = Paginator(product_list, 12)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    
    context = {
        'products': products,
        'category_slug': category_slug,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'shop/product_list.html', context)

def product_detail(request, slug):
    """Product detail view"""
    product = get_object_or_404(
        Product.objects.prefetch_related('variants'),
        slug=slug, is_active=True
    )
    
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id).prefetch_related('variants')[:4]
    
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(
            user=request.user, product=product
        ).exists()
    
    context = {
        'product': product,
        'related_products': related_products,
        'in_wishlist': in_wishlist,
    }
    return render(request, 'shop/product_detail.html', context)


def product_data_api(request, product_id):
    """API endpoint to get product data for quick add modal"""
    try:
        product = Product.objects.prefetch_related('variants').get(
            id=product_id, is_active=True
        )
        
        variants_data = []
        for variant in product.variants.all():
            variants_data.append({
                'id': variant.id,
                'size': variant.size,
                'stock': variant.stock,
            })
        
        in_wishlist = False
        if request.user.is_authenticated:
            in_wishlist = Wishlist.objects.filter(
                user=request.user, product=product
            ).exists()
        
        data = {
            'success': True,
            'id': product.id,
            'name': product.name,
            'price': str(product.price),
            'image': product.image.url if product.image else None,
            'variants': variants_data,
            'in_wishlist': in_wishlist,
        }
        return JsonResponse(data)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)


# ============================================
# AUTHENTICATION VIEWS WITH VERIFICATION
# ============================================

def login_view(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=identifier, password=password)
            
            if user is None:
                try:
                    user_obj = User.objects.get(email=identifier)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if user is not None:
                # Check if user is verified
                if not user.is_active:
                    # User exists but not verified - redirect to verification
                    request.session['verification_user_id'] = user.id
                    request.session['verification_email'] = user.email
                    request.session['verification_phone'] = user.profile.phone if hasattr(user, 'profile') else None
                    
                    messages.warning(request, 'Please verify your account before logging in.')
                    return redirect('verify_account')
                
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                
                Cart.objects.get_or_create(user=user)
                
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('home')
            else:
                messages.error(request, 'Invalid credentials. Please try again.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'shop/login.html', {'form': form})


def register_view(request):
    """Registration view with phone number - sends to verification"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save user (inactive) and create profile with phone
                    user = form.save()
                    
                    # Store ALL session keys for verification
                    request.session['verification_user_id'] = user.id
                    request.session['verification_type'] = 'email'
                    request.session['verification_email'] = user.email
                    request.session['verification_phone'] = form.cleaned_data.get('phone')
                    
                    # Send OTP email (this creates the VerificationCode internally)
                    email_sent = send_email_otp(user, user.email)
                    
                    if email_sent:
                        messages.info(request, 'Please verify your account. Check your email for the verification code.')
                    else:
                        messages.warning(request, 'Failed to send verification email. Please try resending or contact support.')
                    
                    return redirect('verify_account')
                    
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                messages.error(request, 'An error occurred. Please try again.')
        else:
            # Form has errors - display them
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegisterForm()
    
    return render(request, 'shop/register.html', {'form': form})

def verify_account_view(request):
    """Handle OTP verification for new accounts"""
    # Check if user came from registration
    user_id = request.session.get('verification_user_id')
    
    if not user_id:
        messages.error(request, 'Please register first.')
        return redirect('register')
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, 'Invalid verification session. Please register again.')
        return redirect('register')
    
    # If user is already active, redirect to home
    if user.is_active and profile.email_verified:
        messages.success(request, 'Your account is already verified!')
        return redirect('home')
    
    # Get contact info for display
    email = request.session.get('verification_email', user.email)
    phone = profile.phone if profile.phone else None
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        
        if not otp_code or len(otp_code) != 6:
            messages.error(request, 'Please enter a valid 6-digit code.')
            return render(request, 'shop/verify_account.html', {
                'email': email,
                'phone': phone
            })
        
        try:
            # Find the verification code
            verification = VerificationCode.objects.filter(
                user=user,
                code=otp_code,
                verification_type='email',
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
            
            # Mark as used
            verification.is_used = True
            verification.save()
            
            # Activate user and profile
            user.is_active = True
            user.save()
            
            profile.email_verified = True
            profile.is_fully_verified = True
            profile.save()
            
            # Clear session - ONLY delete keys that exist
            keys_to_delete = ['verification_user_id', 'verification_email', 'verification_type', 'verification_phone']
            for key in keys_to_delete:
                if key in request.session:
                    del request.session[key]
            
            messages.success(request, 'Your account has been verified! Please log in.')
            return redirect('login')
            
        except VerificationCode.DoesNotExist:
            messages.error(request, 'Invalid or expired verification code. Please try again.')
            return render(request, 'shop/verify_account.html', {
                'email': email,
                'phone': phone
            })
    
    return render(request, 'shop/verify_account.html', {
        'email': email,
        'phone': phone
    })


@require_http_methods(["POST"])
def resend_otp_view(request):
    """Resend OTP via email or phone"""
    user_id = request.session.get('verification_user_id')
    
    if not user_id:
        return JsonResponse({
            'success': False,
            'error': 'Session expired. Please register again.'
        }, status=400)
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'User not found. Please register again.'
        }, status=400)
    
    resend_type = request.POST.get('type', 'email')
    
    # Check for recent codes (rate limiting - 60 seconds)
    recent_code = VerificationCode.objects.filter(
        user=user,
        verification_type=resend_type,
        created_at__gt=timezone.now() - timezone.timedelta(seconds=60)
    ).first()
    
    if recent_code:
        return JsonResponse({
            'success': False,
            'error': 'Please wait 60 seconds before requesting a new code.'
        }, status=429)
    
    # Generate new code
    try:
        if resend_type == 'email':
            # Deactivate user until verified (in case they were activated)
            if user.is_active:
                user.is_active = False
                user.save()
            
            # Create new email verification code
            verification = VerificationCode.objects.create(
                user=user,
                verification_type='email',
                email=user.email,
                expires_at=timezone.now() + timezone.timedelta(minutes=10)
            )
            
            # Send email
            send_email_otp(user, user.email)
            
            return JsonResponse({
                'success': True,
                'message': f'Verification code sent to {user.email}'
            })
            
        elif resend_type == 'phone' and profile.phone:
            # Create new phone verification code
            verification = VerificationCode.objects.create(
                user=user,
                verification_type='phone',
                phone=profile.phone,
                expires_at=timezone.now() + timezone.timedelta(minutes=10)
            )
            
            # TODO: Implement SMS sending here
            # For now, just return success (you'll need to add SMS service)
            
            return JsonResponse({
                'success': True,
                'message': f'Verification code sent to {profile.phone}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Phone number not provided.'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error resending OTP: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to send verification code. Please try again.'
        }, status=500)

@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ============================================
# CART VIEWS
# ============================================

@login_required
def cart_view(request):
    """Cart page view"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('variant__product').all()
    
    recommended_products = Product.objects.filter(
        is_active=True
    ).exclude(
        id__in=[item.variant.product.id for item in cart_items]
    ).prefetch_related('variants')[:4]
    
    context = {
        'cart_items': cart_items,
        'cart_subtotal': cart.get_subtotal(),
        'cart_total': cart.get_total(),
        'recommended_products': recommended_products,
    }
    return render(request, 'shop/cart.html', context)


@login_required
def cart_api(request):
    """API endpoint to get cart data"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('variant__product').all()
    
    items_data = []
    for item in items:
        items_data.append({
            'id': item.id,
            'name': item.variant.product.name,
            'price': str(item.variant.product.price),
            'size': item.variant.size,
            'quantity': item.quantity,
            'image': item.variant.product.image.url if item.variant.product.image else None,
            'total': str(item.get_total()),
        })
    
    data = {
        'success': True,
        'count': cart.get_total_items(),
        'items': items_data,
        'subtotal': str(cart.get_subtotal()),
        'total': str(cart.get_total()),
    }
    return JsonResponse(data)


@login_required
@require_POST
def add_to_cart(request, product_id):
    """Add product to cart"""
    try:
        product = Product.objects.prefetch_related('variants').get(
            id=product_id, is_active=True
        )
        
        variant_id = request.POST.get('variant_id')
        size = request.POST.get('size')
        quantity = int(request.POST.get('quantity', 1))
        
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        elif size:
            variant = get_object_or_404(ProductVariant, size=size, product=product)
        else:
            variant = product.variants.filter(stock__gt=0).first()
            if not variant:
                return JsonResponse({'success': False, 'error': 'Product is out of stock'}, status=400)
        
        if variant.stock < quantity:
            return JsonResponse({
                'success': False,
                'error': f'Only {variant.stock} items available'
            }, status=400)
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {variant.stock} items available'
                }, status=400)
            cart_item.quantity = new_quantity
            cart_item.save()
        
        variant.stock -= quantity
        variant.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Item added to cart',
            'cart_count': cart.get_total_items()
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def quick_add_to_cart(request):
    """Quick add product to cart"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        product_id = data.get('product_id')
        variant_id = data.get('variant_id')
        size = data.get('size')
        quantity = int(data.get('quantity', 1))
        
        product = Product.objects.prefetch_related('variants').get(
            id=product_id, is_active=True
        )
        
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        elif size:
            variant = get_object_or_404(ProductVariant, size=size, product=product)
        else:
            variant = product.variants.filter(stock__gt=0).first()
            if not variant:
                return JsonResponse({'success': False, 'error': 'Product is out of stock'}, status=400)
        
        if variant.stock < quantity:
            return JsonResponse({
                'success': False,
                'error': f'Only {variant.stock} items available'
            }, status=400)
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {variant.stock} items available'
                }, status=400)
            cart_item.quantity = new_quantity
            cart_item.save()
        
        variant.stock -= quantity
        variant.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Item added to cart',
            'cart_count': cart.get_total_items()
        })
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        variant = cart_item.variant
        
        if quantity <= 0:
            variant.stock += cart_item.quantity
            variant.save()
            cart_item.delete()
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'cart_count': cart_item.cart.get_total_items()
            })
        
        quantity_diff = quantity - cart_item.quantity
        
        if quantity_diff > 0 and variant.stock < quantity_diff:
            return JsonResponse({
                'success': False,
                'error': f'Only {variant.stock} more items available'
            }, status=400)
        
        variant.stock -= quantity_diff
        variant.save()
        
        cart_item.quantity = quantity
        cart_item.save()
        
        cart = cart_item.cart
        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'cart_count': cart.get_total_items(),
            'item_total': str(cart_item.get_total()),
            'cart_subtotal': str(cart.get_subtotal()),
            'cart_total': str(cart.get_total())
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        variant = cart_item.variant
        cart = cart_item.cart
        
        variant.stock += cart_item.quantity
        variant.save()
        
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_count': cart.get_total_items(),
            'cart_subtotal': str(cart.get_subtotal()),
            'cart_total': str(cart.get_total())
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# WISHLIST VIEWS
# ============================================

@login_required
def wishlist_view(request):
    """Wishlist page view"""
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product').prefetch_related('product__variants')
    
    context = {'wishlist_items': wishlist_items}
    return render(request, 'shop/wishlist.html', context)


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    """Toggle product in wishlist"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        wishlist_item = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).first()
        
        if wishlist_item:
            wishlist_item.delete()
            in_wishlist = False
            message = 'Removed from wishlist'
        else:
            Wishlist.objects.create(user=request.user, product=product)
            in_wishlist = True
            message = 'Added to wishlist'
        
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'in_wishlist': in_wishlist,
            'wishlist_count': wishlist_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def wishlist_api(request):
    """API endpoint to get wishlist data"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    items_data = []
    for item in wishlist_items:
        items_data.append({
            'id': item.id,
            'product_id': item.product.id,
            'name': item.product.name,
            'price': str(item.product.price),
            'image': item.product.image.url if item.product.image else None,
            'slug': item.product.slug,
        })
    
    return JsonResponse({'success': True, 'count': len(items_data), 'items': items_data})


@login_required
def move_to_cart(request, wishlist_id):
    """Move item from wishlist to cart"""
    try:
        wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
        product = wishlist_item.product
        
        variant = product.variants.filter(stock__gt=0).first()
        
        if not variant:
            messages.error(request, 'This product is currently out of stock.')
            return redirect('wishlist')
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': 1}
        )
        
        if not created:
            if cart_item.quantity < variant.stock:
                cart_item.quantity += 1
                cart_item.save()
                variant.stock -= 1
                variant.save()
            else:
                messages.warning(request, 'Maximum available quantity already in cart.')
                return redirect('wishlist')
        else:
            variant.stock -= 1
            variant.save()
        
        wishlist_item.delete()
        
        messages.success(request, f'{product.name} moved to cart.')
        return redirect('wishlist')
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('wishlist')


# ============================================
# CHECKOUT & ORDER VIEWS
# ============================================

@login_required
def checkout_view(request):
    """Enhanced checkout view with shipping calculation"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('variant__product').all()
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')
    
    profile = request.user.profile
    
    # Check if user is verified
    if not profile.is_fully_verified:
        messages.warning(request, 'Please verify your account to complete checkout.')
        return redirect('profile')
    
    # Pre-fill form
    initial_data = {
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'phone': profile.phone,
        'address': profile.address,
        'city': profile.city,
        'region': profile.region,
        'postal_code': profile.postal_code,
        'country': profile.country,
    }
    
    # Get shipping methods
    shipping_methods = ShippingMethod.objects.filter(is_active=True)
    
    # Calculate shipping options
    cart_weight = cart.get_total_weight()
    cart_subtotal = cart.get_subtotal()
    
    shipping_options = []
    for method in shipping_methods:
        cost = calculate_shipping_cost(
            method=method,
            weight_kg=cart_weight,
            subtotal=cart_subtotal,
            region=profile.region,
            user=request.user
        )
        shipping_options.append({
            'method': method,
            'cost': cost,
            'free_shipping': cost == 0
        })
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Get selected shipping method
            shipping_method_type = form.cleaned_data['shipping_method']
            shipping_method = ShippingMethod.objects.get(method_type=shipping_method_type)
            
            # Calculate shipping cost
            shipping_cost = calculate_shipping_cost(
                method=shipping_method,
                weight_kg=cart_weight,
                subtotal=cart_subtotal,
                region=form.cleaned_data.get('region'),
                user=request.user
            )
            
            # Check for promotion code
            promotion_code = form.cleaned_data.get('promotion_code', '')
            discount_amount = 0
            promotion = None
            
            if promotion_code:
                try:
                    promotion = Promotion.objects.get(code=promotion_code.upper(), is_active=True)
                    valid, message = promotion.is_valid(request.user, cart_subtotal)
                    if valid:
                        discount_amount = promotion.calculate_discount(cart_subtotal)
                    else:
                        messages.warning(request, message)
                except Promotion.DoesNotExist:
                    messages.warning(request, 'Invalid promotion code.')
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                address=form.cleaned_data['address'],
                apartment=form.cleaned_data.get('apartment', ''),
                city=form.cleaned_data['city'],
                region=form.cleaned_data.get('region', ''),
                postal_code=form.cleaned_data['postal_code'],
                country=form.cleaned_data['country'],
                payment_method=form.cleaned_data['payment_method'],
                shipping_method=shipping_method_type,
                shipping_cost=shipping_cost,
                subtotal=cart_subtotal,
                discount_amount=discount_amount,
                total=cart_subtotal + shipping_cost - discount_amount,
                free_shipping_applied=shipping_cost == 0 and cart_subtotal < 3000,
                welcome_discount_applied=discount_amount > 0 and not profile.first_order_completed
            )
            
            # Create order items
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.variant.product,
                    variant=cart_item.variant,
                    product_name=cart_item.variant.product.name,
                    variant_size=cart_item.variant.size,
                    price=cart_item.variant.product.price,
                    quantity=cart_item.quantity
                )
            
            # Track promotion use
            if promotion and discount_amount > 0:
                UserPromotionUse.objects.create(
                    user=request.user,
                    promotion=promotion,
                    order=order,
                    discount_amount=discount_amount
                )
                promotion.total_uses += 1
                promotion.save()
            
            # Clear cart
            cart.items.all().delete()
            
            # Redirect to payment if not COD
            if order.payment_method != 'cod':
                return redirect('payment_process', order_number=order.order_number)
            
            messages.success(request, 'Order placed successfully!')
            return redirect('order_confirmation', order_number=order.order_number)
    else:
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'cart_subtotal': cart_subtotal,
        'cart_total': cart.get_total(),
        'shipping_options': shipping_options,
        'is_first_order': not profile.first_order_completed,
        'is_verified': profile.is_fully_verified,
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def calculate_shipping_api(request):
    """API to calculate shipping cost dynamically"""
    try:
        method_type = request.GET.get('method', 'standard')
        region = request.GET.get('region', '')
        
        cart = request.user.cart
        weight = cart.get_total_weight()
        subtotal = cart.get_subtotal()
        
        method = get_object_or_404(ShippingMethod, method_type=method_type, is_active=True)
        cost = calculate_shipping_cost(method, weight, subtotal, region, request.user)
        
        return JsonResponse({
            'success': True,
            'shipping_cost': float(cost),
            'subtotal': float(subtotal),
            'total': float(subtotal + cost),
            'free_shipping': cost == 0
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ============================================
# PAYMENT VIEWS
# ============================================

@login_required
def payment_process_view(request, order_number):
    """Process payment for order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if not order.can_pay():
        messages.error(request, 'This order cannot be paid for.')
        return redirect('order_detail', order_number=order.order_number)
    
    payment_method = order.payment_method
    
    # Create payment record
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            'gateway': payment_method,
            'amount': order.total,
            'status': 'pending'
        }
    )
    
    context = {
        'order': order,
        'payment': payment,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    
    if payment_method == 'card':
        # Initialize Stripe
        try:
            intent = create_payment_intent(order)
            context['client_secret'] = intent.client_secret
        except Exception as e:
            messages.error(request, f'Payment initialization failed: {str(e)}')
            return redirect('checkout')
        return render(request, 'shop/payment/stripe.html', context)
    
    elif payment_method == 'gcash':
        return render(request, 'shop/payment/gcash.html', context)
    
    elif payment_method == 'maya':
        return render(request, 'shop/payment/maya.html', context)
    
    elif payment_method == 'paypal':
        return render(request, 'shop/payment/paypal.html', context)
    
    return redirect('order_confirmation', order_number=order.order_number)


@login_required
@require_POST
def process_payment_api(request, order_number):
    """API to process payment"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    payment = order.payment
    
    try:
        data = json.loads(request.body)
        payment_method = order.payment_method
        
        if payment_method == 'card':
            # Stripe payment
            payment_intent_id = data.get('payment_intent_id')
            result = process_stripe_payment(payment, payment_intent_id)
        
        elif payment_method == 'gcash':
            # GCash payment via Xendit/PayMongo
            result = process_gcash_payment(payment, data)
        
        elif payment_method == 'maya':
            # Maya payment
            result = process_maya_payment(payment, data)
        
        elif payment_method == 'paypal':
            # PayPal payment
            result = process_paypal_payment(payment, data)
        
        else:
            return JsonResponse({'success': False, 'error': 'Invalid payment method'})
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('order_confirmation', kwargs={'order_number': order.order_number})
            })
        else:
            return JsonResponse({'success': False, 'error': result.get('error', 'Payment failed')})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook handler"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        # Log webhook
        PaymentWebhookLog.objects.create(
            gateway='stripe',
            event_type=event['type'],
            payload=event
        )
        
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            # Update payment status
            payment = Payment.objects.filter(gateway_transaction_id=payment_intent['id']).first()
            if payment:
                payment.mark_completed(payment_intent['id'])
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            payment = Payment.objects.filter(gateway_transaction_id=payment_intent['id']).first()
            if payment:
                error_message = payment_intent.get('last_payment_error', {}).get('message', 'Payment failed')
                payment.mark_failed(error_message)
        
        return HttpResponse(status=200)
    
    except Exception as e:
        return HttpResponse(status=400)


@csrf_exempt
def gcash_webhook(request):
    """GCash/Xendit webhook handler"""
    try:
        payload = json.loads(request.body)
        
        PaymentWebhookLog.objects.create(
            gateway='gcash',
            event_type=payload.get('status', 'unknown'),
            payload=payload
        )
        
        # Process based on status
        reference = payload.get('reference_id')
        if reference:
            payment = Payment.objects.filter(gateway_reference=reference).first()
            if payment:
                if payload.get('status') == 'SUCCESS':
                    payment.mark_completed(payload.get('id'))
                elif payload.get('status') in ['FAILED', 'EXPIRED']:
                    payment.mark_failed(payload.get('failure_code', 'Payment failed'))
        
        return HttpResponse(status=200)
    
    except Exception as e:
        return HttpResponse(status=400)


@csrf_exempt
def maya_webhook(request):
    """Maya webhook handler"""
    try:
        payload = json.loads(request.body)
        
        PaymentWebhookLog.objects.create(
            gateway='maya',
            event_type=payload.get('status', 'unknown'),
            payload=payload
        )
        
        reference = payload.get('requestReferenceNumber')
        if reference:
            payment = Payment.objects.filter(gateway_reference=reference).first()
            if payment:
                if payload.get('status') == 'PAYMENT_SUCCESS':
                    payment.mark_completed(payload.get('paymentTokenId'))
                elif payload.get('status') == 'PAYMENT_FAILED':
                    payment.mark_failed(payload.get('error', 'Payment failed'))
        
        return HttpResponse(status=200)
    
    except Exception as e:
        return HttpResponse(status=400)


# ============================================
# ORDER VIEWS
# ============================================

@login_required
def order_confirmation_view(request, order_number):
    """Order confirmation page"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {'order': order}
    return render(request, 'shop/order_confirmation.html', context)


@login_required
def order_detail_view(request, order_number):
    """Order detail page"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number,
        user=request.user
    )
    
    context = {'order': order}
    return render(request, 'shop/order_detail.html', context)


@login_required
@require_POST
def cancel_order(request, order_number):
    """Cancel order"""
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        if order.can_cancel():
            for item in order.items.all():
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
            
            order.cancel()
            messages.success(request, 'Order cancelled successfully.')
        else:
            messages.error(request, 'This order cannot be cancelled.')
        
        return redirect('profile')
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('profile')


# ============================================
# PROFILE VIEWS
# ============================================

@login_required
def profile_view(request):
    """User profile page"""
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related('items').order_by('-created_at')
    
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            form = UserProfileForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully.')
        
        elif form_type == 'password':
            password_form = PasswordChangeForm(request.POST)
            if password_form.is_valid():
                current_password = password_form.cleaned_data['current_password']
                new_password = password_form.cleaned_data['new_password']
                
                if request.user.check_password(current_password):
                    request.user.set_password(new_password)
                    request.user.save()
                    messages.success(request, 'Password changed successfully. Please log in again.')
                    return redirect('login')
                else:
                    messages.error(request, 'Current password is incorrect.')
    
    profile_form = UserProfileForm(instance=profile)
    password_form = PasswordChangeForm()
    
    context = {
        'orders': orders,
        'profile_form': profile_form,
        'password_form': password_form,
        'profile': profile,
    }
    return render(request, 'shop/profile.html', context)


# ============================================
# UTILITY VIEWS
# ============================================

def get_cart_count(request):
    """Get cart item count for navbar"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        return cart.get_total_items()
    return 0


def get_wishlist_count(request):
    """Get wishlist item count for navbar"""
    if request.user.is_authenticated:
        return Wishlist.objects.filter(user=request.user).count()
    return 0
