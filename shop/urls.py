from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.product_list, name='product_list'),
    path('shop/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:item_id>/<str:action>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('cart/api/', views.cart_api, name='cart_api'),
    path('checkout/', views.order_create, name='order_create'),
    path('order/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order/<int:order_id>/status/', views.check_order_status, name='check_order_status'),
    path('variant/<int:variant_id>/stock/', views.check_variant_stock, name='check_variant_stock'),
]