from django.contrib import admin
from .models import Category, Product, ProductVariant, CartItem, Order, OrderItem

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['size', 'stock', 'sku']
    readonly_fields = ['sku']

# Define this BEFORE OrderAdmin
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = ['product', 'variant', 'price', 'quantity']
    extra = 0

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'get_total_stock', 'available', 'created']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'available']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]
    search_fields = ['name', 'description']
    date_hierarchy = 'created'

    def get_total_stock(self, obj):
        return obj.get_total_stock()
    get_total_stock.short_description = 'Total Stock'

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'stock', 'sku']
    list_filter = ['size']
    search_fields = ['product__name', 'sku']
    list_editable = ['stock']
    readonly_fields = ['sku']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'phone', 'payment_method', 'status', 'total', 'created']
    list_filter = ['status', 'payment_method', 'created']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'address']
    inlines = [OrderItemInline]  # Now it's defined above!
    readonly_fields = ['created', 'updated', 'confirmed_at']
    
    fieldsets = (
        ('Customer Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'postal_code', 'latitude', 'longitude')
        }),
        ('Payment', {
            'fields': ('payment_method', 'total')
        }),
        ('Status', {
            'fields': ('status', 'created', 'updated', 'confirmed_at')
        }),
    )
    
    actions = ['confirm_orders', 'mark_shipped']
    
    def confirm_orders(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='confirmed', confirmed_at=timezone.now())
    confirm_orders.short_description = "Mark selected orders as confirmed"
    
    def mark_shipped(self, request, queryset):
        queryset.update(status='shipped')
    mark_shipped.short_description = "Mark selected orders as shipped"

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'variant', 'quantity', 'created']