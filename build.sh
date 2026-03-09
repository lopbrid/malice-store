#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "=========================================="
echo "🔍 Checking migration status BEFORE running migrations..."
python manage.py showmigrations

echo "=========================================="
echo "📊 Checking if database tables exist..."
python manage.py shell << EOF
from django.db import connection
from django.db.utils import ProgrammingError

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM shop_product LIMIT 1")
    print("✅ Table 'shop_product' already exists!")
except ProgrammingError:
    print("❌ Table 'shop_product' does NOT exist - migrations needed")
EOF

echo "=========================================="
echo "🏃 Running migrations with verbose output..."
python manage.py migrate -v 3

echo "=========================================="
echo "🔍 Checking migration status AFTER running migrations..."
python manage.py showmigrations

echo "=========================================="
echo "📊 Verifying tables exist after migrations..."
python manage.py shell << EOF
from django.db import connection
from django.db.utils import ProgrammingError

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM shop_product LIMIT 1")
    print("✅ Table 'shop_product' exists now!")
except ProgrammingError:
    print("❌ Table 'shop_product' STILL does NOT exist!")
EOF

echo "Creating default shipping methods and regions (if not exists)..."
python manage.py shell << EOF
from shop.models import ShippingMethod, ShippingRegion, ShippingRate

# First check if product table exists (to know if migrations ran)
from django.db import connection
from django.db.utils import ProgrammingError

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM shop_product LIMIT 1")
    tables_exist = True
except ProgrammingError:
    tables_exist = False

if not tables_exist:
    print("⚠️ Database tables not ready yet. Skipping shipping data creation.")
else:
    # Only create if no shipping methods exist
    if not ShippingMethod.objects.exists():
        print("No shipping data found. Creating default data...")
        
        # Create shipping methods
        methods = [
            {'name': 'Standard Shipping', 'method_type': 'standard', 'estimated_days_min': 3, 'estimated_days_max': 5, 'sort_order': 1},
            {'name': 'Express Shipping', 'method_type': 'express', 'estimated_days_min': 1, 'estimated_days_max': 2, 'sort_order': 2},
            {'name': 'Same-Day Delivery', 'method_type': 'same_day', 'estimated_days_min': 0, 'estimated_days_max': 0, 'sort_order': 3},
            {'name': 'International Shipping', 'method_type': 'international', 'estimated_days_min': 7, 'estimated_days_max': 14, 'sort_order': 4},
        ]
        
        for method_data in methods:
            ShippingMethod.objects.get_or_create(method_type=method_data['method_type'], defaults=method_data)
            print(f"✓ Created shipping method: {method_data['name']}")
        
        # Create default regions
        regions = [
            {'name': 'Metro Manila', 'code': 'MM', 'country': 'PH'},
            {'name': 'Luzon', 'code': 'LUZ', 'country': 'PH'},
            {'name': 'Visayas', 'code': 'VIS', 'country': 'PH'},
            {'name': 'Mindanao', 'code': 'MIN', 'country': 'PH'},
        ]
        
        for region_data in regions:
            ShippingRegion.objects.get_or_create(code=region_data['code'], defaults=region_data)
            print(f"✓ Created shipping region: {region_data['name']}")
        
        # Get shipping methods for rates
        standard = ShippingMethod.objects.get(method_type='standard')
        express = ShippingMethod.objects.get(method_type='express')
        
        # Standard shipping rates
        ShippingRate.objects.get_or_create(
            shipping_method=standard,
            region=None,
            weight_min=0,
            weight_max=999,
            defaults={'base_cost': 150, 'cost_per_kg': 0, 'free_shipping_threshold': 3000}
        )
        print("✓ Created standard shipping rate")
        
        # Express shipping rates
        ShippingRate.objects.get_or_create(
            shipping_method=express,
            region=None,
            weight_min=0,
            weight_max=999,
            defaults={'base_cost': 350, 'cost_per_kg': 0, 'free_shipping_threshold': None}
        )
        print("✓ Created express shipping rate")
        
        print("\n✅ Default shipping data created successfully!")
    else:
        print("✅ Shipping data already exists, skipping creation.")
EOF

echo "=========================================="
echo "✅ Build completed successfully!"
echo "=========================================="