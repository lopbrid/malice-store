from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Product, ProductVariant, Category, CartItem, Order, OrderItem
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re
from django.urls import reverse
from django.db import models

def user_login(request):
    """User login with email or phone + password"""
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', 'home')
        
        user = None
        
        # Try to authenticate by email
        if '@' in identifier:
            try:
                user_obj = User.objects.get(email=identifier.lower())
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        else:
            # Try by username (phone number)
            user = authenticate(request, username=identifier, password=password)
        
        if user is not None:
            login(request, user)
            
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            # Check if there was a pending cart addition before login
                        # Check if there was a pending cart addition before login
            pending_product = request.session.pop('pending_cart_product', None)
            if pending_product:
                # Add the pending item to cart
                product = get_object_or_404(Product, id=pending_product)
                size = request.session.pop('pending_cart_size', 'M')
                qty = request.session.pop('pending_cart_qty', 1)
                
                variant = get_object_or_404(ProductVariant, product=product, size=size)
                
                if variant.stock >= qty:
                    item, created = CartItem.objects.get_or_create(
                        user=user,
                        product=product,
                        variant=variant,
                        defaults={'quantity': qty}
                    )
                    if not created:
                        item.quantity += qty
                        item.save()
                    messages.success(request, f'Added {product.name} to your cart!')
                else:
                    messages.error(request, f'Not enough stock for {product.name}')
                
                return redirect('cart_detail')
            
            # IMPORTANT FIX: Check if checkout intent exists
            if request.session.get('checkout_intent'):
                del request.session['checkout_intent']
                return redirect('order_create')
            
            # Otherwise redirect to next URL or home
            return redirect(next_url if next_url else 'home')
        else:
            messages.error(request, 'Invalid email/phone or password.')
    
    # GET request - check if there's a next parameter for checkout
    next_url = request.GET.get('next', '')
    # If next is checkout, set checkout_intent flag
    if 'checkout' in next_url.lower():
        request.session['checkout_intent'] = True
        # Store cart count for display
        cart_count = 0
        if request.session.session_key:
            cart_count = CartItem.objects.filter(session_id=request.session.session_key).aggregate(
                total=models.Sum('quantity')
            )['total'] or 0
        request.session['cart_count'] = int(cart_count)
    
    return render(request, 'shop/login.html', {'next': next_url})
def user_register(request):
    """User registration with phone validation"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        next_url = request.POST.get('next', 'home')
        
        # Validation
        errors = []
        
        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        
        # Email validation
        if not email:
            errors.append('Email is required.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append('Please enter a valid email address.')
            if User.objects.filter(email=email).exists():
                errors.append('This email is already registered.')
        
        # Phone validation
        if not phone:
            errors.append('Phone number is required.')
        else:
            phone_clean = re.sub(r'[\s\-]', '', phone)
            if not re.match(r'^09\d{9}$', phone_clean):
                errors.append('Please enter a valid Philippine mobile number (09XXXXXXXXX).')
            elif User.objects.filter(username=phone_clean).exists():
                errors.append('This phone number is already registered.')
        
        # Password validation
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'shop/register.html', {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'next': next_url,
            })
        
        # Create user
                # Store session key BEFORE creating user (it will change after login)
        old_session_key = request.session.session_key
        
        # Create user
        username = phone_clean
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Log in the user immediately
        login(request, user)
        
        # Restore the old session key to preserve cart
        if old_session_key:
            request.session.cycle_key()
            # Copy old session data to new session
            from django.contrib.sessions.models import Session
            try:
                old_session = Session.objects.get(session_key=old_session_key)
                old_data = old_session.get_decoded()
                for key, value in old_data.items():
                    if key not in request.session:
                        request.session[key] = value
            except Session.DoesNotExist:
                pass
        
        # Log in the user immediately
        login(request, user)
        
        # Merge session cart if exists
                # Merge session cart if exists
               # Merge session cart using OLD session key (before login changed it)
        if old_session_key:
            session_items = CartItem.objects.filter(session_id=old_session_key)
            for item in session_items:
                # Check if user already has this item
                existing = CartItem.objects.filter(
                    user=user,
                    product=item.product,
                    variant=item.variant
                ).first()
                
                if existing:
                    # Add quantities together
                    existing.quantity += item.quantity
                    existing.save()
                else:
                    # Transfer item to user
                    item.user = user
                    item.session_id = None
                    item.save()
        
        messages.success(request, f'✓ Account created successfully! Welcome, {first_name}! You can now complete your order.')
        
        # IMPORTANT FIX: Check if checkout intent exists and redirect accordingly
        if request.session.get('checkout_intent'):
            # Clear the checkout intent flag but keep cart data
            del request.session['checkout_intent']
            # Redirect to checkout page
            return redirect('order_create')
        
        # If next URL is provided and not empty, use it
        if next_url and next_url != 'home':
            return redirect(next_url)
        
        return redirect('home')
    
    # GET request
    next_url = request.GET.get('next', 'home')
    return render(request, 'shop/register.html', {'next': next_url})

@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

@login_required
def user_profile(request):
    """User profile with order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created')
    return render(request, 'shop/profile.html', {
        'user': request.user,
        'orders': orders
    })

@login_required
def cart_update(request, item_id, action):
    """Update cart item quantity with stock checking - requires login"""
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    
    if action == 'increase':
        # Check stock before increasing
        if item.variant.stock > item.quantity:
            item.quantity += 1
            item.save()
            messages.success(request, f'Quantity updated for {item.product.name}')
        else:
            messages.error(request, f'Maximum stock reached for {item.product.name} size {item.variant.size} (Stock: {item.variant.stock})')
    
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
            messages.success(request, f'Quantity updated for {item.product.name}')
        else:
            # Remove if quantity would be 0
            item.delete()
            messages.success(request, 'Item removed from cart')
            return redirect('cart_detail')
    
    return redirect('cart_detail')

def home(request):
    featured = Product.objects.filter(available=True)[:5]
    return render(request, 'shop/home.html', {'featured': featured})

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    filter_type = request.GET.get('category')
    if filter_type == 'new':
        products = products.order_by('-created')[:12]
    elif filter_type == 'best':
        products = products.order_by('?')[:12]
    
    return render(request, 'shop/product_list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query,
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    variants = product.variants.all().order_by('size')
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'variants': variants,
    })

@login_required
def cart_detail(request):
    """Cart detail - requires login"""
    cart_items = CartItem.objects.filter(user=request.user).select_related('product', 'variant')
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'shop/cart.html', {'cart_items': cart_items, 'total': total})

@require_POST
def cart_add(request, product_id):
    """Add to cart - requires login to prevent session sharing issues"""
    # Require login for adding to cart
    if not request.user.is_authenticated:
        messages.info(request, 'Please sign in to add items to your cart.')
        # Store the product they wanted to add
        request.session['pending_cart_product'] = product_id
        request.session['pending_cart_size'] = request.POST.get('size', 'M')
        request.session['pending_cart_qty'] = int(request.POST.get('quantity', 1))
        return redirect(f"{reverse('login')}?next={reverse('product_detail', args=[get_object_or_404(Product, id=product_id).slug])}")
    
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size', 'M')
    quantity = int(request.POST.get('quantity', 1))
    
    # Get variant
    variant = get_object_or_404(ProductVariant, product=product, size=size)
    
    # Check stock
    if variant.stock < quantity:
        messages.error(request, f'Only {variant.stock} items available in size {size}')
        return redirect('product_detail', slug=product.slug)
    
    # Only authenticated users can have carts now
    item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        variant=variant,
        defaults={'quantity': quantity}
    )
    if not created:
        item.quantity += quantity
        item.save()
    
    messages.success(request, f'Added {product.name} (Size {size}) to cart')
    return redirect('cart_detail')

@login_required
def cart_remove(request, item_id):
    """Remove item from cart - requires login"""
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    messages.success(request, 'Item removed from cart')
    return redirect('cart_detail')

def order_create(request):
    """Create order - requires login at checkout"""
    cart_items = []
    
    # Get cart items for both guest and logged-in users
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related('product', 'variant')
    else:
        session_id = request.session.session_key
        if session_id:
            cart_items = CartItem.objects.filter(session_id=session_id).select_related('product', 'variant')
    
    if not cart_items:
        messages.error(request, 'Your cart is empty')
        return redirect('cart_detail')
    
    # If not logged in, redirect to login with "checkout" intent
    if not request.user.is_authenticated:
        # Store checkout intent in session
        request.session['checkout_intent'] = True
        request.session['cart_count'] = sum(item.quantity for item in cart_items)
        messages.info(request, 'Please sign in or create an account to complete your order.')
        return redirect(f"{reverse('login')}?next={reverse('order_create')}")
    
    # User is logged in - proceed with checkout
    total = sum(item.total_price() for item in cart_items)
    
    # Pre-fill with user data
    initial_data = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'phone': request.user.username,  # Phone stored as username
    }
    
    if request.method == 'POST':
        # Validate stock
        for item in cart_items:
            if item.variant.stock < item.quantity:
                messages.error(request, f'Not enough stock for {item.product.name} size {item.variant.size}')
                return redirect('cart_detail')
        
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        postal_code = request.POST.get('postal_code')
        
        # Validate required fields
        if not all([first_name, last_name, email, phone, address, city, postal_code]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'shop/checkout.html', {
                'cart_items': cart_items,
                'total': total,
                'initial_data': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone,
                }
            })
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            postal_code=postal_code,
            payment_method=request.POST.get('payment_method', 'cod'),
            latitude=request.POST.get('latitude') or None,
            longitude=request.POST.get('longitude') or None,
            total=total,
            status='pending'
        )
        
        # Create order items and reduce stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                price=item.product.price,
                quantity=item.quantity
            )
            item.variant.stock -= item.quantity
            item.variant.save()
        
        # Clear cart
        cart_items.delete()
        
        # Clear checkout intent
        if 'checkout_intent' in request.session:
            del request.session['checkout_intent']
        
        messages.success(request, 'Order placed successfully! We will confirm your order soon.')
        return redirect('order_confirmation', order_id=order.id)
    
    return render(request, 'shop/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'initial_data': initial_data,
    })

def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'shop/order_confirmation.html', {'order': order})

def check_order_status(request, order_id):
    """AJAX endpoint to check if order is confirmed"""
    order = get_object_or_404(Order, id=order_id)
    return JsonResponse({
        'status': order.status,
        'confirmed': order.status == 'confirmed',
        'shipped': order.status == 'shipped',
    })

@login_required
def cart_api(request):
    """Cart API - requires login"""
    cart_items = CartItem.objects.filter(user=request.user).select_related('product', 'variant')
    
    items_data = []
    subtotal = 0
    
    for item in cart_items:
        item_total = item.total_price()
        subtotal += item_total
        items_data.append({
            'id': item.id,
            'name': item.product.name,
            'size': item.variant.size if item.variant else 'N/A',
            'price': str(item.product.price),
            'quantity': item.quantity,
            'total': str(item_total),
            'image': item.product.image.url if item.product.image else None,
        })
    
    total = subtotal
    
    return JsonResponse({
        'items': items_data,
        'subtotal': str(subtotal),
        'total': str(total),
        'count': sum(item['quantity'] for item in items_data)
    })

def check_variant_stock(request, variant_id):
    """Check if variant has stock"""
    variant = get_object_or_404(ProductVariant, id=variant_id)
    return JsonResponse({
        'stock': variant.stock,
        'available': variant.stock > 0
    })