from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category,
    Product,
    ProductVariant,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Wishlist,
    UserProfile
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
        'total_stock', 'is_active', 'is_featured', 'is_new', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_featured', 'is_new', 'is_best_seller',
        'category', 'created_at'
    ]
    search_fields = ['name', 'description', 'variants__sku']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'is_featured', 'is_new']
    inlines = [ProductVariantInline]
    date_hierarchy = 'created_at'
    actions = ['make_active', 'make_inactive', 'make_featured', 'make_new']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category', 'image')
        }),
        ('Pricing', {
            'fields': ('price',),
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
            if hasattr(subtotal, 'replace'):  # Check if it's a string-like object
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


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'variant', 'product_name', 'variant_size', 'price', 'quantity', 'total_display']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def total_display(self, obj):
        # Convert to float explicitly to ensure it's a number, not a SafeString
        try:
            total_value = float(obj.total)
            return format_html('₱{:,.2f}', total_value)
        except (TypeError, ValueError):
            return format_html('₱0.00')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'user', 'status_badge', 'payment_method',
        'total_display', 'created_at', 'actions_buttons'
    ]
    list_filter = [
        'status', 'payment_method', 'shipping_method',
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
                'apartment', 'city', 'postal_code', 'country'
            )
        }),
        ('Order Details', {
            'fields': ('payment_method', 'shipping_method', 'shipping_cost', 'subtotal', 'total')
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('shipped_at', 'delivered_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#fbbf24',
            'confirmed': '#60a5fa',
            'shipped': '#c084fc',
            'delivered': '#22c55e',
            'cancelled': '#ef4444',
        }
        bg_colors = {
            'pending': 'rgba(251, 191, 36, 0.2)',
            'confirmed': 'rgba(96, 165, 250, 0.2)',
            'shipped': 'rgba(192, 132, 252, 0.2)',
            'delivered': 'rgba(34, 197, 94, 0.2)',
            'cancelled': 'rgba(239, 68, 68, 0.2)',
        }
        return format_html(
            '<span style="background: {}; color: {}; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;">{}</span>',
            bg_colors.get(obj.status, '#666'),
            colors.get(obj.status, '#fff'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def total_display(self, obj):
        # Convert to float explicitly to ensure it's a number, not a SafeString
        try:
            # Try to convert to float if it's a string or other type
            if hasattr(obj.total, 'replace'):  # Check if it's a string-like object
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
        if obj.status in ['pending', 'confirmed']:
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
        queryset.filter(status='pending').update(status='confirmed')
    mark_confirmed.short_description = 'Mark selected orders as confirmed'
    
    def mark_shipped(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status__in=['pending', 'confirmed']).update(
            status='shipped', shipped_at=timezone.now()
        )
    mark_shipped.short_description = 'Mark selected orders as shipped'
    
    def mark_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.filter(status='shipped').update(
            status='delivered', delivered_at=timezone.now()
        )
    mark_delivered.short_description = 'Mark selected orders as delivered'
    
    def mark_cancelled(self, request, queryset):
        from django.utils import timezone
        for order in queryset.filter(status__in=['pending', 'confirmed']):
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
            'Payment', 'Shipping', 'Subtotal', 'Shipping Cost', 'Total'
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
                order.total
            ])
        
        return response
    export_orders.short_description = 'Export selected orders to CSV'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'country', 'newsletter_subscribed']
    search_fields = ['user__username', 'user__email', 'phone', 'city']
    list_filter = ['newsletter_subscribed', 'country']


# Customize admin site
def customize_admin_site():
    admin.site.site_header = 'MALICE Admin'
    admin.site.site_title = 'MALICE - E-Commerce Management'
    admin.site.index_title = 'Dashboard'

customize_admin_site()
