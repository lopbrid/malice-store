from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
import json

from .models import (
    Product, Category, ProductVariant, Cart, CartItem,
    Wishlist, Order, OrderItem, UserProfile
)
from .forms import (
    CustomAuthenticationForm, CustomUserCreationForm,
    CheckoutForm, UserProfileForm, PasswordChangeForm
)


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
    
    context = {
        'featured': featured_products,
        'new_arrivals': new_arrivals,
        'best_sellers': best_sellers,
    }
    return render(request, 'shop/home.html', context)


def product_list(request):
    """Product list view with filtering and sorting"""
    products = Product.objects.filter(is_active=True).prefetch_related('variants')
    
    # Get query parameters
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    sort_by = request.GET.get('sort', 'newest')
    
    # Filter by category
    if category_slug:
        if category_slug == 'new':
            products = products.filter(is_new=True)
        elif category_slug == 'best':
            products = products.filter(is_best_seller=True)
        else:
            products = products.filter(category__slug=category_slug)
    
    # Search
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Sorting
    if sort_by == 'price-low':
        products = products.order_by('price')
    elif sort_by == 'price-high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:  # newest
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
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
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id).prefetch_related('variants')[:4]
    
    # Check if product is in user's wishlist
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


# ==================== AUTHENTICATION VIEWS ====================

def login_view(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            password = form.cleaned_data['password']
            
            # Try to authenticate with username first
            user = authenticate(request, username=identifier, password=password)
            
            # If that fails, try with email
            if user is None:
                try:
                    user_obj = User.objects.get(email=identifier)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                
                # Ensure user has a cart
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
    """Registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to MALICE.')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'shop/register.html', {'form': form})


@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ==================== CART VIEWS ====================

@login_required
def cart_view(request):
    """Cart page view"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('variant__product').all()
    
    # Get recommended products
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
    """Add product to cart - FIXED: Now properly decreases stock"""
    try:
        product = Product.objects.prefetch_related('variants').get(
            id=product_id, is_active=True
        )
        
        # Get variant from request
        variant_id = request.POST.get('variant_id')
        size = request.POST.get('size')
        quantity = int(request.POST.get('quantity', 1))
        
        # Find variant
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        elif size:
            variant = get_object_or_404(ProductVariant, size=size, product=product)
        else:
            # Use first available variant
            variant = product.variants.filter(stock__gt=0).first()
            if not variant:
                return JsonResponse({
                    'success': False,
                    'error': 'Product is out of stock'
                }, status=400)
        
        # Check stock
        if variant.stock < quantity:
            return JsonResponse({
                'success': False,
                'error': f'Only {variant.stock} items available'
            }, status=400)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Update quantity
            new_quantity = cart_item.quantity + quantity
            if new_quantity > variant.stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {variant.stock} items available'
                }, status=400)
            cart_item.quantity = new_quantity
            cart_item.save()
        
        # FIX: Decrease stock when adding to cart
        variant.stock -= quantity
        variant.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Item added to cart',
            'cart_count': cart.get_total_items()
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def quick_add_to_cart(request):
    """Quick add product to cart - FIXED: Now properly decreases stock"""
    try:
        # Handle both JSON and form data
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
        
        # Find variant
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
        elif size:
            variant = get_object_or_404(ProductVariant, size=size, product=product)
        else:
            variant = product.variants.filter(stock__gt=0).first()
            if not variant:
                return JsonResponse({
                    'success': False,
                    'error': 'Product is out of stock'
                }, status=400)
        
        # Check stock
        if variant.stock < quantity:
            return JsonResponse({
                'success': False,
                'error': f'Only {variant.stock} items available'
            }, status=400)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get or create cart item
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
        
        # FIX: Decrease stock when adding to cart
        variant.stock -= quantity
        variant.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Item added to cart',
            'cart_count': cart.get_total_items()
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity - FIXED: Properly manages stock adjustments"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        variant = cart_item.variant
        
        if quantity <= 0:
            # Restore stock and delete item
            variant.stock += cart_item.quantity
            variant.save()
            cart_item.delete()
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'cart_count': cart_item.cart.get_total_items()
            })
        
        # Calculate difference between new and current quantity
        quantity_diff = quantity - cart_item.quantity
        
        # If increasing quantity, check if enough stock
        if quantity_diff > 0 and variant.stock < quantity_diff:
            return JsonResponse({
                'success': False,
                'error': f'Only {variant.stock} more items available'
            }, status=400)
        
        # FIX: Adjust stock based on quantity change
        # If quantity_diff is positive (increasing), stock decreases
        # If quantity_diff is negative (decreasing), stock increases
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
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart - FIXED: Properly restores stock before deleting"""
    try:
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        variant = cart_item.variant
        cart = cart_item.cart
        
        # FIX: Restore stock before deleting item
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
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ==================== WISHLIST VIEWS ====================

@login_required
def wishlist_view(request):
    """Wishlist page view"""
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product').prefetch_related('product__variants')
    
    context = {
        'wishlist_items': wishlist_items,
    }
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
        
        # Get updated wishlist count
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        
        return JsonResponse({
            'success': True,
            'message': message,
            'in_wishlist': in_wishlist,
            'wishlist_count': wishlist_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def wishlist_api(request):
    """API endpoint to get wishlist data"""
    wishlist_items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product')
    
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
    
    return JsonResponse({
        'success': True,
        'count': len(items_data),
        'items': items_data
    })


@login_required
def move_to_cart(request, wishlist_id):
    """Move item from wishlist to cart - FIXED: Properly manages stock"""
    try:
        wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
        product = wishlist_item.product
        
        # Get first available variant
        variant = product.variants.filter(stock__gt=0).first()
        
        if not variant:
            messages.error(request, 'This product is currently out of stock.')
            return redirect('wishlist')
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            variant=variant,
            defaults={'quantity': 1}
        )
        
        if not created:
            # Already in cart, check if we can add more
            if cart_item.quantity < variant.stock:
                cart_item.quantity += 1
                cart_item.save()
                # Decrease stock for the additional item
                variant.stock -= 1
                variant.save()
            else:
                messages.warning(request, 'Maximum available quantity already in cart.')
                return redirect('wishlist')
        else:
            # New item in cart, decrease stock
            variant.stock -= 1
            variant.save()
        
        # Remove from wishlist
        wishlist_item.delete()
        
        messages.success(request, f'{product.name} moved to cart.')
        return redirect('wishlist')
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('wishlist')


# ==================== CHECKOUT & ORDER VIEWS ====================

@login_required
def checkout_view(request):
    """Checkout page view"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.select_related('variant__product').all()
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')
    
    # Pre-fill form with user data
    initial_data = {
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
    }
    
    # Try to get profile data
    try:
        profile = request.user.profile
        initial_data.update({
            'phone': profile.phone,
            'address': profile.address,
            'city': profile.city,
            'postal_code': profile.postal_code,
            'country': profile.country,
        })
    except UserProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
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
                postal_code=form.cleaned_data['postal_code'],
                country=form.cleaned_data['country'],
                payment_method=form.cleaned_data['payment_method'],
                shipping_method=form.cleaned_data['shipping_method'],
                shipping_cost=0 if cart.get_subtotal() >= 3000 else (150 if form.cleaned_data['shipping_method'] == 'standard' else 350),
                subtotal=cart.get_subtotal(),
                total=cart.get_total()
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
            
            # Clear cart (stock already decreased when added to cart)
            cart.items.all().delete()
            
            messages.success(request, 'Order placed successfully!')
            return redirect('order_confirmation', order_number=order.order_number)
    else:
        form = CheckoutForm(initial=initial_data)
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'cart_subtotal': cart.get_subtotal(),
        'cart_total': cart.get_total(),
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def order_confirmation_view(request, order_number):
    """Order confirmation page"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'shop/order_confirmation.html', context)


@login_required
def order_detail_view(request, order_number):
    """Order detail page"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number,
        user=request.user
    )
    
    context = {
        'order': order,
    }
    return render(request, 'shop/order_detail.html', context)


@login_required
@require_POST
def cancel_order(request, order_number):
    """Cancel order - FIXED: Restores stock when cancelling"""
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        if order.can_cancel():
            # Restore stock for all items
            for item in order.items.all():
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
            
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save()
            
            messages.success(request, 'Order cancelled successfully.')
        else:
            messages.error(request, 'This order cannot be cancelled.')
        
        return redirect('profile')
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('profile')


# ==================== PROFILE VIEWS ====================

@login_required
def profile_view(request):
    """User profile page"""
    orders = Order.objects.filter(
        user=request.user
    ).prefetch_related('items').order_by('-created_at')
    
    # Get or create profile
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


# ==================== UTILITY VIEWS ====================

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


# Import User model at the end to avoid circular import
from django.contrib.auth.models import User