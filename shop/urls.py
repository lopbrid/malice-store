from django.urls import path
from .views import test_email
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Products
    path('shop/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('api/product/<int:product_id>/', views.product_data_api, name='product_data_api'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify-account/', views.verify_account_view, name='verify_account'),  # This should exist
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),  # This should exist
    path('logout/', views.logout_view, name='logout'),
    
    # Cart
    path('cart/', views.cart_view, name='cart'),
    path('cart/api/', views.cart_api, name='cart_api'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/quick-add/', views.quick_add_to_cart, name='quick_add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/api/', views.wishlist_api, name='wishlist_api'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/move-to-cart/<int:wishlist_id>/', views.move_to_cart, name='move_to_cart'),
    
    # Checkout & Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('api/shipping/calculate/', views.calculate_shipping_api, name='calculate_shipping'),
    
    # Payment
    path('payment/process/<str:order_number>/', views.payment_process_view, name='payment_process'),
    path('api/payment/process/<str:order_number>/', views.process_payment_api, name='process_payment_api'),
    
    # Payment Webhooks
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('webhooks/gcash/', views.gcash_webhook, name='gcash_webhook'),
    path('webhooks/maya/', views.maya_webhook, name='maya_webhook'),
    
    # Order Confirmation & Details
    path('order/confirmation/<str:order_number>/', views.order_confirmation_view, name='order_confirmation'),
    path('order/<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('order/cancel/<str:order_number>/', views.cancel_order, name='cancel_order'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('test-email/', views.test_email_render, name='test_email'),
     path("test-email/", test_email),
]
