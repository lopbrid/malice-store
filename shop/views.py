from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Product, ProductVariant, Category, CartItem, Order, OrderItem

def cart_update(request, item_id, action):
    """Update cart item quantity"""
    item = get_object_or_404(CartItem, id=item_id)
    
    if action == 'increase':
        # Check stock before increasing
        if item.variant.stock > item.quantity:
            item.quantity += 1
            item.save()
        else:
            messages.error(request, f'Maximum stock reached for {item.product.name} size {item.variant.size}')
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
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

def cart_detail(request):
    cart_items = []
    total = 0
    
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related('product', 'variant')
    else:
        session_id = request.session.session_key
        if session_id:
            cart_items = CartItem.objects.filter(session_id=session_id).select_related('product', 'variant')
    
    total = sum(item.total_price() for item in cart_items)
    return render(request, 'shop/cart.html', {'cart_items': cart_items, 'total': total})

@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    size = request.POST.get('size', 'M')
    quantity = int(request.POST.get('quantity', 1))
    
    # Get variant
    variant = get_object_or_404(ProductVariant, product=product, size=size)
    
    # Check stock
    if variant.stock < quantity:
        messages.error(request, f'Only {variant.stock} items available in size {size}')
        return redirect('product_detail', slug=product.slug)
    
    if request.user.is_authenticated:
        item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()
    else:
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        
        item, created = CartItem.objects.get_or_create(
            session_id=session_id,
            product=product,
            variant=variant,
            defaults={'quantity': quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()
    
    messages.success(request, f'Added {product.name} (Size {size}) to cart')
    return redirect('cart_detail')

def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.delete()
    messages.success(request, 'Item removed from cart')
    return redirect('cart_detail')

def order_create(request):
    cart_items = []
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related('product', 'variant')
    else:
        session_id = request.session.session_key
        if session_id:
            cart_items = CartItem.objects.filter(session_id=session_id).select_related('product', 'variant')
    
    if not cart_items:
        messages.error(request, 'Your cart is empty')
        return redirect('cart_detail')
    
    total = sum(item.total_price() for item in cart_items)
    
    if request.method == 'POST':
        # Validate stock before creating order
        for item in cart_items:
            if item.variant.stock < item.quantity:
                messages.error(request, f'Not enough stock for {item.product.name} size {item.variant.size}')
                return redirect('cart_detail')
        
        # Create order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            postal_code=request.POST.get('postal_code'),
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
            # Reduce stock
            item.variant.stock -= item.quantity
            item.variant.save()
        
        # Clear cart
        cart_items.delete()
        
        messages.success(request, 'Order placed successfully! We will confirm your order soon.')
        return redirect('order_confirmation', order_id=order.id)
    
    return render(request, 'shop/checkout.html', {
        'cart_items': cart_items,
        'total': total,
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

def cart_api(request):
    cart_items = []
    
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user).select_related('product', 'variant')
    else:
        session_id = request.session.session_key
        if session_id:
            cart_items = CartItem.objects.filter(session_id=session_id).select_related('product', 'variant')
    
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