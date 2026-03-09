"""
Context processors for MALICE shop
"""
from .models import Cart, Wishlist, Category


def cart_context(request):
    """Add cart data to all templates"""
    context = {
        'cart_count': 0,
        'cart_items': [],
        'cart_subtotal': 0,
        'cart_total': 0,
    }
    
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            context['cart_count'] = cart.get_total_items()
            context['cart_items'] = cart.items.select_related('variant__product').all()
            context['cart_subtotal'] = cart.get_subtotal()
            context['cart_total'] = cart.get_total()
        except:
            pass
    
    return context


def site_settings(request):
    """Add site-wide settings to all templates"""
    from django.conf import settings
    
    return {
        'SITE_NAME': 'MALICE',
        'FREE_SHIPPING_THRESHOLD': getattr(settings, 'FREE_SHIPPING_THRESHOLD', 3000),
        'STRIPE_PUBLIC_KEY': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
        'categories': Category.objects.filter(is_active=True),
    }
