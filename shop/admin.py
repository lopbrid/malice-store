from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Product, ProductVariant, Cart, CartItem,
    Order, OrderItem, Wishlist, UserProfile,
    ShippingMethod, ShippingRate, ShippingRegion,
    VerificationCode, Payment, PaymentWebhookLog,
    Promotion, UserPromotionUse
)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'variant', 'quantity', 'added_at']
    search_fields = ['cart__user__username', 'variant__product__name']
    list_filter = ['added_at']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    date_hierarchy = 'created_at'
    
    def product_count(self, obj):
        count = obj.products.count()
        url = reverse('admin:shop_product_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} products</a>', url, count)
    product_count.short_description = 'Products'


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['size', 'stock', 'sku']
    readonly_fields = ['sku']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'thumbnail', 'name', 'price_display', 'category',
        'total_stock', 'weight_kg', 'is_active', 'is_featured', 'is_new', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_featured', 'is_new', 'is_best_seller',
        'category', 'created_at'
    ]
    search_fields = ['name', 'description', 'variants__sku']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'is_featured', 'is_new', 'weight_kg']
    inlines = [ProductVariantInline]
    date_hierarchy = 'created_at'
    actions = ['make_active', 'make_inactive', 'make_featured', 'make_new']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category', 'image')
        }),
        ('Pricing & Weight', {
            'fields': ('price', 'weight_kg'),
        }),
        ('Status & Flags', {
            'fields': ('is_active', 'is_featured', 'is_new', 'is_best_seller'),
            'classes': ('collapse',)
        }),
    )
    
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return format_html(
            '<div style="width: 50px; height: 50px; background: #333; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #666; font-size: 10px;">No Image</div>'
        )
    thumbnail.short_description = 'Image'
    
    def price_display(self, obj):
        if obj.price:
            return format_html("₱{}", f"{obj.price:,.2f}")
        return "-"
    price_display.short_description = "Price"
    
    def total_stock(self, obj):
        stock = obj.get_total_stock()
        if stock == 0:
            return format_html('<span style="color: #ef4444; font-weight: bold;">Out of Stock</span>')
        elif stock < 5:
            return format_html('<span style="color: #fbbf24; font-weight: bold;">{} left</span>', stock)
        return format_html('<span style="color: #22c55e;">{}</span>', stock)
    total_stock.short_description = 'Stock'
    
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
    make_active.short_description = 'Mark selected products as active'
    
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
    make_inactive.short_description = 'Mark selected products as inactive'
    
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
    make_featured.short_description = 'Mark selected products as featured'
    
    def make_new(self, request, queryset):
        queryset.update(is_new=True)
    make_new.short_description = 'Mark selected products as new arrivals'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'stock', 'sku']
    list_filter = ['size', 'product__category']
    search_fields = ['product__name', 'sku']
    list_editable = ['stock']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['variant', 'quantity', 'added_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_count', 'subtotal_display', 'created_at']
    search_fields = ['user__username', 'user__email']
    inlines = [CartItemInline]
    readonly_fields = ['user', 'created_at', 'updated_at']
    
    def item_count(self, obj):
        return obj.get_total_items()
    item_count.short_description = 'Items'
    
    def subtotal_display(self, obj):
        try:
            subtotal = obj.get_subtotal()
            if hasattr(subtotal, 'replace'):
                subtotal_value = float(str(subtotal).replace('₱', '').replace(',', ''))
            else:
                subtotal_value = float(subtotal)
            return format_html('₱{:,.2f}', subtotal_value)
        except (TypeError, ValueError, AttributeError):
            return format_html('₱0.00')
    subtotal_display.short_description = 'Subtotal'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__name']
    list_filter = ['created_at']
    date_hierarchy = 'created_at'


# ============================================
# SHIPPING ADMIN
# ============================================

@admin.register(ShippingRegion)
class ShippingRegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'country', 'is_active']
    list_filter = ['country', 'is_active']
    search_fields = ['name', 'code']
    list_editable = ['is_active']


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'method_type', 'estimated_delivery', 'is_active', 'sort_order']
    list_filter = ['method_type', 'is_active']
    list_editable = ['is_active', 'sort_order']
    search_fields = ['name', 'description']
    
    def estimated_delivery(self, obj):
        return obj.get_estimated_delivery()
    estimated_delivery.short_description = 'Estimated Delivery'


@admin.register(ShippingRate)
class ShippingRateAdmin(admin.ModelAdmin):
    list_display = ['shipping_method', 'region', 'weight_range', 'base_cost', 'cost_per_kg', 'is_active']
    list_filter = ['shipping_method', 'region', 'is_active']
    list_editable = ['base_cost', 'cost_per_kg', 'is_active']
    search_fields = ['shipping_method__name', 'region__name']
    
    def weight_range(self, obj):
        return f"{obj.weight_min} - {obj.weight_max} kg"
    weight_range.short_description = 'Weight Range'


# ============================================
# USER PROFILE & VERIFICATION ADMIN
# ============================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'phone_verified', 'email_verified', 'is_fully_verified', 
                    'city', 'country', 'first_order_completed', 'newsletter_subscribed']
    list_filter = ['phone_verified', 'email_verified', 'is_fully_verified', 
                   'first_order_completed', 'newsletter_subscribed', 'country']
    search_fields = ['user__username', 'user__email', 'phone', 'city']
    list_editable = ['phone_verified', 'email_verified', 'newsletter_subscribed']


# In shop/admin.py - add this if not already present

@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'verification_type', 'code_masked', 'is_used', 'is_valid', 'created_at', 'expires_at']
    list_filter = ['verification_type', 'is_used', 'created_at']
    search_fields = ['user__username', 'email', 'phone']
    readonly_fields = ['code', 'created_at', 'used_at']
    date_hierarchy = 'created_at'
    
    def code_masked(self, obj):
        return f"****{obj.code[-2:]}" if obj.code else "-"
    code_masked.short_description = 'Code'
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Valid'


# ============================================
# ORDER ADMIN
# ============================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'variant', 'product_name', 'variant_size', 'price', 'quantity', 'total_display']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def total_display(self, obj):
        try:
            total_value = float(obj.get_total())
            return format_html('₱{:,.2f}', total_value)
        except (TypeError, ValueError):
            return format_html('₱0.00')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'status_badge', 'payment_method',
        'total_display', 'free_shipping_applied', 'created_at', 'actions_buttons'
    ]
    list_filter = [
        'status', 'payment_method', 'shipping_method',
        'free_shipping_applied', 'welcome_discount_applied',
        'created_at', 'country'
    ]
    search_fields = [
        'order_number', 'user__username', 'user__email',
        'email', 'phone', 'first_name', 'last_name'
    ]
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    actions = [
        'mark_confirmed', 'mark_shipped', 'mark_delivered',
        'mark_cancelled', 'export_orders'
    ]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Shipping Address', {
            'fields': (
                'first_name', 'last_name', 'address',
                'apartment', 'city', 'region', 'postal_code', 'country'
            )
        }),
        ('Order Details', {
            'fields': ('payment_method', 'shipping_method', 'shipping_cost', 'subtotal', 'discount_amount', 'total')
        }),
        ('Promotions', {
            'fields': ('free_shipping_applied', 'welcome_discount_applied'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('shipped_at', 'delivered_at', 'cancelled_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#fbbf24', 'awaiting_payment': '#f97316', 'payment_failed': '#ef4444',
            'confirmed': '#60a5fa', 'processing': '#a78bfa',
            'shipped': '#c084fc', 'delivered': '#22c55e',
            'cancelled': '#ef4444', 'refunded': '#6b7280',
        }
        bg_colors = {
            'pending': 'rgba(251, 191, 36, 0.2)', 'awaiting_payment': 'rgba(249, 115, 22, 0.2)',
            'payment_failed': 'rgba(239, 68, 68, 0.2)', 'confirmed': 'rgba(96, 165, 250, 0.2)',
            'processing': 'rgba(167, 139, 250, 0.2)', 'shipped': 'rgba(192, 132, 252, 0.2)',
            'delivered': 'rgba(34, 197, 94, 0.2)', 'cancelled': 'rgba(239, 68, 68, 0.2)',
            'refunded': 'rgba(107, 114, 128, 0.2)',
        }
        return format_html(
            '<span style="background: {}; color: {}; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;">{}</span>',
            bg_colors.get(obj.status, '#666'),
            colors.get(obj.status, '#fff'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def total_display(self, obj):
        try:
            if hasattr(obj.total, 'replace'):
                total_value = float(str(obj.total).replace('₱', '').replace(',', ''))
            else:
                total_value = float(obj.total)
            return format_html('₱{:,.2f}', total_value)
        except (TypeError, ValueError, AttributeError):
            return format_html('₱0.00')
    total_display.short_description = 'Total'
    
    def actions_buttons(self, obj):
        buttons = []
        if obj.status == 'pending':
            buttons.append(
                format_html('<a href="{}" class="button" style="background: #60a5fa; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; margin-right: 4px; font-size: 11px;">Confirm</a>', 
                reverse('admin:shop_order_change', args=[obj.id]))
            )
        if obj.status in ['pending', 'confirmed', 'awaiting_payment']:
            buttons.append(
                format_html('<a href="{}" class="button" style="background: #c084fc; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; margin-right: 4px; font-size: 11px;">Ship</a>',
                reverse('admin:shop_order_change', args=[obj.id]))
            )
        if obj.can_cancel():
            buttons.append(
                format_html('<a href="{}" class="button" style="background: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">Cancel</a>',
                reverse('admin:shop_order_change', args=[obj.id]))
            )
        return mark_safe(''.join(buttons)) if buttons else '-'
    actions_buttons.short_description = 'Quick Actions'
    
    def mark_confirmed(self, request, queryset):
        queryset.filter(status__in=['pending', 'awaiting_payment', 'payment_failed']).update(status='confirmed')
    mark_confirmed.short_description = 'Mark selected orders as confirmed'
    
    def mark_shipped(self, request, queryset):
        queryset.filter(status__in=['pending', 'confirmed', 'awaiting_payment']).update(
            status='shipped', shipped_at=timezone.now()
        )
    mark_shipped.short_description = 'Mark selected orders as shipped'
    
    def mark_delivered(self, request, queryset):
        queryset.filter(status='shipped').update(
            status='delivered', delivered_at=timezone.now()
        )
    mark_delivered.short_description = 'Mark selected orders as delivered'
    
    def mark_cancelled(self, request, queryset):
        for order in queryset.filter(status__in=['pending', 'confirmed', 'awaiting_payment', 'payment_failed']):
            order.cancel()
    mark_cancelled.short_description = 'Mark selected orders as cancelled'
    
    def export_orders(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Order Number', 'Date', 'Customer', 'Email', 'Status',
            'Payment', 'Shipping', 'Subtotal', 'Shipping Cost', 'Discount', 'Total'
        ])
        
        for order in queryset:
            writer.writerow([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                f"{order.first_name} {order.last_name}",
                order.email,
                order.get_status_display(),
                order.get_payment_method_display(),
                order.get_shipping_method_display(),
                order.subtotal,
                order.shipping_cost,
                order.discount_amount,
                order.total
            ])
        
        return response
    export_orders.short_description = 'Export selected orders to CSV'


# ============================================
# PAYMENT ADMIN
# ============================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'gateway', 'status_badge', 'amount_display', 'created_at', 'completed_at']
    list_filter = ['gateway', 'status', 'created_at']
    search_fields = ['order__order_number', 'gateway_transaction_id', 'gateway_reference']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    date_hierarchy = 'created_at'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#fbbf24', 'processing': '#60a5fa',
            'completed': '#22c55e', 'failed': '#ef4444',
            'refunded': '#6b7280', 'cancelled': '#9ca3af',
        }
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def amount_display(self, obj):
        return format_html('₱{:,.2f}', float(obj.amount))
    amount_display.short_description = 'Amount'


@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['gateway', 'event_type', 'processed', 'created_at']
    list_filter = ['gateway', 'processed', 'created_at']
    search_fields = ['event_type', 'payload']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


# ============================================
# PROMOTION ADMIN
# ============================================

class UserPromotionUseInline(admin.TabularInline):
    model = UserPromotionUse
    extra = 0
    readonly_fields = ['user', 'order', 'discount_amount', 'used_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'promotion_type', 'value_display', 'is_active', 
                    'total_uses', 'start_date', 'end_date']
    list_filter = ['promotion_type', 'is_active', 'for_new_users_only', 'for_verified_users_only']
    search_fields = ['name', 'code', 'description']
    list_editable = ['is_active']
    inlines = [UserPromotionUseInline]
    
    def value_display(self, obj):
        if obj.promotion_type == 'free_shipping':
            return 'Free Shipping'
        elif obj.promotion_type == 'percentage' and obj.percentage_value:
            return f"{obj.percentage_value}%"
        elif obj.promotion_type == 'fixed' and obj.fixed_value:
            return f"₱{obj.fixed_value:,.2f}"
        return '-'
    value_display.short_description = 'Value'


@admin.register(UserPromotionUse)
class UserPromotionUseAdmin(admin.ModelAdmin):
    list_display = ['user', 'promotion', 'order', 'discount_amount', 'used_at']
    list_filter = ['used_at']
    search_fields = ['user__username', 'promotion__name', 'order__order_number']
    date_hierarchy = 'used_at'


# Customize admin site
def customize_admin_site():
    admin.site.site_header = 'MALICE Admin'
    admin.site.site_title = 'MALICE - E-Commerce Management'
    admin.site.index_title = 'Dashboard'

customize_admin_site()

from django.utils import timezone
