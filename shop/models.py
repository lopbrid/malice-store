from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator
from django.db.models import Sum
import uuid
from cloudinary.models import CloudinaryField
import random
import string


# ============================================
# CATEGORY & PRODUCT MODELS
# ============================================

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0.5, help_text="Weight in kilograms")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    image = CloudinaryField('image', folder='products', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    def get_total_stock(self):
        return sum(variant.stock for variant in self.variants.all())

    def has_variants(self):
        return self.variants.exists()

    def is_in_stock(self):
        return self.get_total_stock() > 0


class ProductVariant(models.Model):
    SIZE_CHOICES = [
        ('XS', 'Extra Small'), ('S', 'Small'), ('M', 'Medium'),
        ('L', 'Large'), ('XL', 'Extra Large'), ('XXL', '2XL'), ('ONE', 'One Size'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True, blank=True)

    class Meta:
        unique_together = ['product', 'size']
        ordering = ['size']

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{slugify(self.product.name[:3]).upper()}-{self.size}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.size}"


# ============================================
# USER PROFILE & VERIFICATION MODELS
# ============================================

class UserProfile(models.Model):
    COUNTRY_CHOICES = [
        ('PH', 'Philippines'), ('US', 'United States'), ('SG', 'Singapore'),
        ('JP', 'Japan'), ('OTHER', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, validators=[
        RegexValidator(regex=r'^[\+]?[0-9\s\-\(\)]{10,20}$', message='Enter a valid phone number.')
    ])
    email_otp_created_at = models.DateTimeField(null=True, blank=True)
    phone_otp_created_at = models.DateTimeField(null=True, blank=True)
    email_otp_attempts = models.PositiveIntegerField(default=0)
    phone_otp_attempts = models.PositiveIntegerField(default=0)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    is_fully_verified = models.BooleanField(default=False)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, choices=COUNTRY_CHOICES, default='PH')
    region = models.CharField(max_length=100, blank=True, help_text="State/Province/Region")
    newsletter_subscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Promotion tracking
    first_order_completed = models.BooleanField(default=False)
    welcome_discount_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile - {self.user.username}"

    def check_verification_status(self):
        """Check if user is fully verified"""
        self.is_fully_verified = self.email_verified and self.phone_verified
        self.save(update_fields=['is_fully_verified'])
        return self.is_fully_verified


# In shop/models.py - ensure this model exists

class VerificationCode(models.Model):
    VERIFICATION_TYPE_CHOICES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('password_reset', 'Password Reset'),
        ('2fa', 'Two-Factor Authentication'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=10)
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPE_CHOICES)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.verification_type} - {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.digits, k=6))
        if not self.expires_at:
            from django.conf import settings
            self.expires_at = timezone.now() + timezone.timedelta(minutes=getattr(settings, 'OTP_EXPIRY_MINUTES', 10))
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now() and self.attempts < self.max_attempts

    def verify(self, code):
        """Verify the provided code"""
        if not self.is_valid():
            return False, "Code has expired or maximum attempts reached"
        
        self.attempts += 1
        self.save(update_fields=['attempts'])
        
        if self.code == code:
            self.is_used = True
            self.used_at = timezone.now()
            self.save(update_fields=['is_used', 'used_at'])
            return True, "Verification successful"
        
        remaining = self.max_attempts - self.attempts
        return False, f"Invalid code. {remaining} attempts remaining."


# ============================================
# SHIPPING MODELS
# ============================================

class ShippingRegion(models.Model):
    """Geographic regions for shipping"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    country = models.CharField(max_length=2, default='PH')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ShippingMethod(models.Model):
    """Available shipping methods"""
    METHOD_CHOICES = [
        ('standard', 'Standard Shipping'),
        ('express', 'Express Shipping'),
        ('same_day', 'Same-Day Delivery'),
        ('international', 'International Shipping'),
    ]

    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=METHOD_CHOICES, unique=True)
    description = models.TextField(blank=True)
    estimated_days_min = models.PositiveIntegerField(default=3)
    estimated_days_max = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_estimated_delivery(self):
        if self.estimated_days_min == self.estimated_days_max:
            return f"{self.estimated_days_min} business days"
        return f"{self.estimated_days_min}-{self.estimated_days_max} business days"


class ShippingRate(models.Model):
    """Shipping rates based on region, weight, and method"""
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.CASCADE, related_name='rates')
    region = models.ForeignKey(ShippingRegion, on_delete=models.CASCADE, related_name='shipping_rates', null=True, blank=True)
    
    # Weight ranges (in kg)
    weight_min = models.DecimalField(max_digits=8, decimal_places=3, default=0)
    weight_max = models.DecimalField(max_digits=8, decimal_places=3, default=999)
    
    # Pricing
    base_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Free shipping threshold
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['shipping_method', 'region', 'weight_min']
        unique_together = ['shipping_method', 'region', 'weight_min', 'weight_max']

    def __str__(self):
        region_name = self.region.name if self.region else "All Regions"
        return f"{self.shipping_method.name} - {region_name} ({self.weight_min}-{self.weight_max}kg)"

    def calculate_cost(self, weight_kg, subtotal=0):
        """Calculate shipping cost for given weight and subtotal"""
        # Check free shipping threshold
        if self.free_shipping_threshold and subtotal >= self.free_shipping_threshold:
            return 0
        
        # Calculate base cost + weight surcharge
        weight_surcharge = max(0, (weight_kg - 1)) * float(self.cost_per_kg)
        total = float(self.base_cost) + weight_surcharge
        return round(total, 2)


# ============================================
# CART MODELS
# ============================================

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.user.username}"

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    def get_subtotal(self):
        return sum(item.get_total() for item in self.items.all())

    def get_total_weight(self):
        """Calculate total weight of cart items"""
        return sum(
            item.variant.product.weight_kg * item.quantity 
            for item in self.items.select_related('variant__product').all()
        )

    def get_shipping_cost(self, shipping_method=None, region=None):
        """Calculate shipping cost based on method and region"""
        if not shipping_method:
            shipping_method = ShippingMethod.objects.filter(method_type='standard', is_active=True).first()
        
        if not shipping_method:
            return 150  # Default fallback
        
        subtotal = self.get_subtotal()
        weight = self.get_total_weight()
        
        # Get applicable rate
        rate = ShippingRate.objects.filter(
            shipping_method=shipping_method,
            region=region,
            weight_min__lte=weight,
            weight_max__gte=weight,
            is_active=True
        ).first()
        
        if rate:
            return rate.calculate_cost(weight, subtotal)
        
        # Fallback to default calculation
        if subtotal >= 3000:
            return 0
        return 150 if shipping_method.method_type == 'standard' else 350

    def get_total(self, shipping_method=None, region=None):
        return self.get_subtotal() + self.get_shipping_cost(shipping_method, region)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'variant']

    def __str__(self):
        return f"{self.variant.product.name} - {self.variant.size} x {self.quantity}"

    def get_total(self):
        return self.variant.product.price * self.quantity


# ============================================
# WISHLIST MODEL
# ============================================

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


# ============================================
# ORDER MODELS
# ============================================

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('payment_failed', 'Payment Failed'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('gcash', 'GCash'),
        ('maya', 'Maya/PayMaya'),
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    SHIPPING_CHOICES = [
        ('standard', 'Standard Shipping'),
        ('express', 'Express Shipping'),
        ('same_day', 'Same-Day Delivery'),
        ('international', 'International Shipping'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Contact Information
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Shipping Address
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.TextField()
    apartment = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='Philippines')
    region = models.CharField(max_length=100, blank=True)
    
    # Order Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cod')
    shipping_method = models.CharField(max_length=20, choices=SHIPPING_CHOICES, default='standard')
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Promotion tracking
    free_shipping_applied = models.BooleanField(default=False)
    welcome_discount_applied = models.BooleanField(default=False)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            date_str = timezone.now().strftime('%Y%m%d')
            last_order = Order.objects.filter(order_number__startswith=f'ORD-{date_str}').order_by('-order_number').first()
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.order_number = f'ORD-{date_str}-{new_num:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number}"

    def get_absolute_url(self):
        return reverse('order_detail', kwargs={'order_number': self.order_number})

    def can_cancel(self):
        return self.status in ['pending', 'awaiting_payment', 'confirmed', 'payment_failed']

    def can_pay(self):
        return self.status in ['pending', 'awaiting_payment', 'payment_failed']

    def cancel(self):
        if self.can_cancel():
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            self.save()
            # Restore stock
            for item in self.items.all():
                if item.variant:
                    item.variant.stock += item.quantity
                    item.variant.save()
            return True
        return False

    def mark_as_paid(self):
        """Mark order as paid"""
        if self.can_pay():
            self.status = 'confirmed'
            self.paid_at = timezone.now()
            self.save()
            
            # Update user profile for first order
            profile = self.user.profile
            if not profile.first_order_completed:
                profile.first_order_completed = True
                profile.save(update_fields=['first_order_completed'])
            
            return True
        return False


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    variant_size = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_name} - {self.variant_size} x {self.quantity}"

    def get_total(self):
        return self.price * self.quantity


# ============================================
# PAYMENT MODELS
# ============================================

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    GATEWAY_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('gcash', 'GCash'),
        ('maya', 'Maya/PayMaya'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('xendit', 'Xendit'),
        ('paymongo', 'PayMongo'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Amounts
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='PHP')
    
    # Gateway-specific IDs
    gateway_transaction_id = models.CharField(max_length=255, blank=True)
    gateway_reference = models.CharField(max_length=255, blank=True)
    
    # Payment details (non-sensitive)
    payment_method_details = models.JSONField(default=dict, blank=True)
    
    # 3D Secure / Authentication
    authentication_url = models.URLField(blank=True)
    authentication_status = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.gateway} - {self.status}"

    def mark_completed(self, gateway_transaction_id=None):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if gateway_transaction_id:
            self.gateway_transaction_id = gateway_transaction_id
        self.save()
        self.order.mark_as_paid()

    def mark_failed(self, error_message='', error_code=''):
        self.status = 'failed'
        self.error_message = error_message
        self.error_code = error_code
        self.save()
        self.order.status = 'payment_failed'
        self.order.save()

    def mark_refunded(self):
        self.status = 'refunded'
        self.save()
        self.order.status = 'refunded'
        self.order.save()


class PaymentWebhookLog(models.Model):
    """Log for payment gateway webhooks"""
    gateway = models.CharField(max_length=20)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    headers = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.gateway} - {self.event_type} - {self.created_at}"


# ============================================
# PROMOTION & DISCOUNT MODELS
# ============================================

class Promotion(models.Model):
    """Promotions and discounts"""
    PROMOTION_TYPE_CHOICES = [
        ('free_shipping', 'Free Shipping'),
        ('percentage', 'Percentage Discount'),
        ('fixed', 'Fixed Amount Discount'),
        ('buy_x_get_y', 'Buy X Get Y'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, blank=True)
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPE_CHOICES)
    description = models.TextField(blank=True)
    
    # Value
    percentage_value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fixed_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Limits
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    max_uses_per_user = models.PositiveIntegerField(default=1)
    
    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Target audience
    for_new_users_only = models.BooleanField(default=False)
    for_verified_users_only = models.BooleanField(default=False)
    
    # Tracking
    total_uses = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def is_valid(self, user=None, order_amount=0):
        """Check if promotion is valid for user and order"""
        now = timezone.now()
        
        if not self.is_active:
            return False, "Promotion is not active"
        
        if now < self.start_date:
            return False, "Promotion has not started yet"
        
        if now > self.end_date:
            return False, "Promotion has expired"
        
        if self.max_uses and self.total_uses >= self.max_uses:
            return False, "Promotion usage limit reached"
        
        if order_amount < self.min_order_amount:
            return False, f"Minimum order amount is ₱{self.min_order_amount}"
        
        if user:
            user_uses = UserPromotionUse.objects.filter(user=user, promotion=self).count()
            if user_uses >= self.max_uses_per_user:
                return False, "You have already used this promotion"
            
            if self.for_new_users_only and user.profile.first_order_completed:
                return False, "This promotion is for new users only"
            
            if self.for_verified_users_only and not user.profile.is_fully_verified:
                return False, "This promotion is for verified users only"
        
        return True, "Valid"

    def calculate_discount(self, order_amount):
        """Calculate discount amount"""
        if self.promotion_type == 'free_shipping':
            return 0  # Shipping cost handled separately
        
        if self.promotion_type == 'percentage' and self.percentage_value:
            discount = order_amount * (self.percentage_value / 100)
        elif self.promotion_type == 'fixed' and self.fixed_value:
            discount = self.fixed_value
        else:
            discount = 0
        
        if self.max_discount_amount:
            discount = min(discount, self.max_discount_amount)
        
        return round(discount, 2)


class UserPromotionUse(models.Model):
    """Track promotion usage per user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promotion_uses')
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='uses')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='promotion_uses')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'order', 'promotion']

    def __str__(self):
        return f"{self.user.username} - {self.promotion.name}"
