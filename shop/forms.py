from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from .models import Order, UserProfile, VerificationCode
from allauth.socialaccount.forms import SignupForm as SocialSignupFormBase



class CustomAuthenticationForm(forms.Form):
    """Custom login form that accepts username or email"""
    identifier = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username or email',
            'autocomplete': 'username'
        }),
        label='Username or Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        }),
        label='Password'
    )
    remember = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Remember me'
    )


class CustomUserCreationForm(UserCreationForm):
    """Custom registration form with phone number for verification"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John',
            'autocomplete': 'given-name'
        }),
        label='First Name'
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Doe',
            'autocomplete': 'family-name'
        }),
        label='Last Name'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com',
            'autocomplete': 'email'
        }),
        label='Email Address'
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'autocomplete': 'username'
        }),
        label='Username',
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        validators=[RegexValidator(
            regex=r'^[\+]?[0-9\s\-\(\)]{10,20}$',
            message='Please enter a valid phone number.'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+63 912 345 6789',
            'autocomplete': 'tel'
        }),
        label='Phone Number'
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password',
            'autocomplete': 'new-password'
        }),
        help_text='Your password must contain at least 8 characters.'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        }),
        help_text='Enter the same password as before, for verification.'
    )
    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='I agree to the Terms and Privacy Policy',
        error_messages={'required': 'You must agree to the Terms and Privacy Policy'}
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'phone', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already registered.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Remove spaces for uniqueness check
        clean_phone = phone.replace(' ', '').replace('-', '')
        if UserProfile.objects.filter(phone__contains=clean_phone).exists():
            raise forms.ValidationError('This phone number is already registered.')
        return phone

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2


class OTPVerificationForm(forms.Form):
    """Form for OTP verification"""
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-input',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'maxlength': '6'
        }),
        label='Verification Code',
        help_text='Enter the 6-digit code sent to your email/phone'
    )

    def clean_otp_code(self):
        code = self.cleaned_data.get('otp_code')
        if not code.isdigit():
            raise forms.ValidationError('Please enter only numbers.')
        return code


class ResendOTPForm(forms.Form):
    """Form to request OTP resend"""
    verification_type = forms.ChoiceField(
        choices=[('email', 'Email'), ('phone', 'SMS')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='email',
        label='Send code via'
    )


class CheckoutForm(forms.ModelForm):
    """Enhanced checkout form with shipping method selection"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        }),
        label='Email Address'
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+63 912 345 6789'
        }),
        label='Phone Number',
        validators=[RegexValidator(
            regex=r'^[\+]?[0-9\s\-\(\)]{10,20}$',
            message='Please enter a valid phone number.'
        )]
    )
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John'
        }),
        label='First Name'
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Doe'
        }),
        label='Last Name'
    )
    address = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123 Main Street'
        }),
        label='Street Address'
    )
    apartment = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apt 4B'
        }),
        label='Apartment, Suite, etc. (Optional)'
    )
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Manila'
        }),
        label='City'
    )
    region = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Metro Manila'
        }),
        label='State/Province'
    )
    postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1000'
        }),
        label='Postal Code'
    )
    country = forms.ChoiceField(
        choices=[
            ('PH', 'Philippines'),
            ('US', 'United States'),
            ('SG', 'Singapore'),
            ('JP', 'Japan'),
            ('OTHER', 'Other'),
        ],
        initial='PH',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Country'
    )
    shipping_method = forms.ChoiceField(
        choices=[],  # Populated dynamically in __init__
        widget=forms.RadioSelect(),
        label='Shipping Method'
    )
    payment_method = forms.ChoiceField(
        choices=[
            ('cod', 'Cash on Delivery'),
            ('gcash', 'GCash'),
            ('maya', 'Maya/PayMaya'),
            ('card', 'Credit/Debit Card'),
            ('paypal', 'PayPal'),
        ],
        initial='cod',
        widget=forms.RadioSelect(),
        label='Payment Method'
    )
    promotion_code = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter promo code (optional)'
        }),
        label='Promo Code'
    )

    class Meta:
        model = Order
        fields = [
            'email', 'phone', 'first_name', 'last_name',
            'address', 'apartment', 'city', 'region', 'postal_code', 'country',
            'shipping_method', 'payment_method', 'promotion_code'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically populate shipping methods
        from .models import ShippingMethod
        methods = ShippingMethod.objects.filter(is_active=True)
        self.fields['shipping_method'].choices = [
            (m.method_type, f"{m.name} - {m.get_estimated_delivery()}") 
            for m in methods
        ]


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile"""
    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'city', 'region', 'postal_code', 'country', 'newsletter_subscribed']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+63 912 345 6789'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your address',
                'rows': 3
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Manila'
            }),
            'region': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Metro Manila'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1000'
            }),
            'country': forms.Select(attrs={'class': 'form-control'}),
            'newsletter_subscribed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PasswordChangeForm(forms.Form):
    """Form for changing password"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password'
        }),
        label='Current Password'
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        label='New Password',
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm New Password'
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('New passwords do not match.')

        return cleaned_data


class PaymentMethodForm(forms.Form):
    """Form for selecting payment method"""
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('gcash', 'GCash'),
        ('maya', 'Maya/PayMaya'),
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(),
        label='Select Payment Method'
    )


class CardPaymentForm(forms.Form):
    """Form for credit/debit card payment (Stripe)"""
    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'inputmode': 'numeric',
            'autocomplete': 'cc-number'
        }),
        label='Card Number'
    )
    expiry_month = forms.CharField(
        max_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'MM',
            'inputmode': 'numeric'
        }),
        label='Expiry Month'
    )
    expiry_year = forms.CharField(
        max_length=4,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'YYYY',
            'inputmode': 'numeric'
        }),
        label='Expiry Year'
    )
    cvv = forms.CharField(
        max_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'inputmode': 'numeric',
            'autocomplete': 'cc-csc'
        }),
        label='CVV'
    )
    card_holder = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John Doe',
            'autocomplete': 'cc-name'
        }),
        label='Card Holder Name'
    )

    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number', '').replace(' ', '')
        if not card_number.isdigit() or len(card_number) < 13:
            raise forms.ValidationError('Please enter a valid card number.')
        return card_number

    def clean_cvv(self):
        cvv = self.cleaned_data.get('cvv', '')
        if not cvv.isdigit() or len(cvv) < 3:
            raise forms.ValidationError('Please enter a valid CVV.')
        return cvv


class GCashPaymentForm(forms.Form):
    """Form for GCash payment"""
    gcash_number = forms.CharField(
        max_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09123456789',
            'inputmode': 'tel'
        }),
        label='GCash Mobile Number',
        validators=[RegexValidator(
            regex=r'^(09|\+639)\d{9}$',
            message='Please enter a valid Philippine mobile number.'
        )]
    )


class MayaPaymentForm(forms.Form):
    """Form for Maya payment"""
    maya_number = forms.CharField(
        max_length=13,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09123456789',
            'inputmode': 'tel'
        }),
        label='Maya Mobile Number',
        validators=[RegexValidator(
            regex=r'^(09|\+639)\d{9}$',
            message='Please enter a valid Philippine mobile number.'
        )]
    )


class ForgotPasswordForm(forms.Form):
    """Form for password reset request"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        }),
        label='Email Address'
    )


class ResetPasswordForm(forms.Form):
    """Form for resetting password with token"""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        label='New Password',
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        label='Confirm New Password'
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')

        return cleaned_data

# In shop/forms.py - add this class

class OTPVerificationForm(forms.Form):
    """Form for OTP verification"""
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'otp-input',
            'placeholder': '------',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'maxlength': '6'
        }),
        label='Verification Code',
        help_text='Enter the 6-digit code sent to your email'
    )

    def clean_otp_code(self):
        code = self.cleaned_data.get('otp_code')
        if not code.isdigit():
            raise forms.ValidationError('Please enter only numbers.')
        return code

class SocialSignupForm(SocialSignupFormBase):
    """Custom form for social signup - collects phone number"""
    
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your phone number',
            'class': 'form-control'
        })
    )
    
    def save(self, request):
        user = super().save(request)
        return user