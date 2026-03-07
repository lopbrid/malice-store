#!/usr/bin/env python
"""
Setup script to create initial data for the MALICE e-commerce system.
Run this after migrations: python setup_data.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from shop.models import Category, Product, ProductVariant


def create_categories():
    """Create default categories"""
    categories = [
        {'name': 'T-Shirts', 'slug': 't-shirts'},
        {'name': 'Hoodies', 'slug': 'hoodies'},
        {'name': 'Pants', 'slug': 'pants'},
        {'name': 'Accessories', 'slug': 'accessories'},
    ]
    
    for cat_data in categories:
        Category.objects.get_or_create(
            slug=cat_data['slug'],
            defaults={'name': cat_data['name']}
        )
    
    print("✓ Categories created")


def create_sample_products():
    """Create sample products"""
    
    # Get categories
    tshirts = Category.objects.get(slug='t-shirts')
    hoodies = Category.objects.get(slug='hoodies')
    
    products_data = [
        {
            'name': 'Essential Black Tee',
            'description': 'A minimalist black t-shirt crafted from premium cotton. Features a relaxed fit and subtle branding. Perfect for everyday wear.',
            'price': 1299.00,
            'category': tshirts,
            'is_featured': True,
            'is_new': True,
            'variants': [
                {'size': 'S', 'stock': 15},
                {'size': 'M', 'stock': 20},
                {'size': 'L', 'stock': 18},
                {'size': 'XL', 'stock': 12},
            ]
        },
        {
            'name': 'Classic White Tee',
            'description': 'Timeless white t-shirt made from soft, breathable fabric. Clean lines and comfortable fit for any occasion.',
            'price': 1199.00,
            'category': tshirts,
            'is_featured': True,
            'is_best_seller': True,
            'variants': [
                {'size': 'S', 'stock': 10},
                {'size': 'M', 'stock': 25},
                {'size': 'L', 'stock': 20},
                {'size': 'XL', 'stock': 15},
            ]
        },
        {
            'name': 'Oversized Hoodie',
            'description': 'Premium oversized hoodie with a relaxed silhouette. Features a kangaroo pocket and ribbed cuffs. Made from heavyweight cotton fleece.',
            'price': 2499.00,
            'category': hoodies,
            'is_featured': True,
            'is_new': True,
            'is_best_seller': True,
            'variants': [
                {'size': 'S', 'stock': 8},
                {'size': 'M', 'stock': 15},
                {'size': 'L', 'stock': 12},
                {'size': 'XL', 'stock': 10},
                {'size': 'XXL', 'stock': 5},
            ]
        },
        {
            'name': 'Minimal Logo Tee',
            'description': 'Subtle branding on a premium cotton tee. Clean design for the modern minimalist.',
            'price': 1499.00,
            'category': tshirts,
            'is_new': True,
            'variants': [
                {'size': 'S', 'stock': 20},
                {'size': 'M', 'stock': 20},
                {'size': 'L', 'stock': 15},
                {'size': 'XL', 'stock': 10},
            ]
        },
        {
            'name': 'Zip-Up Hoodie',
            'description': 'Versatile zip-up hoodie with a modern fit. Perfect for layering. Features side pockets and adjustable hood.',
            'price': 2799.00,
            'category': hoodies,
            'is_featured': True,
            'variants': [
                {'size': 'S', 'stock': 10},
                {'size': 'M', 'stock': 18},
                {'size': 'L', 'stock': 15},
                {'size': 'XL', 'stock': 8},
            ]
        },
        {
            'name': 'Vintage Wash Tee',
            'description': 'Soft-washed cotton tee with a vintage feel. Pre-shrunk for the perfect fit.',
            'price': 1399.00,
            'category': tshirts,
            'is_best_seller': True,
            'variants': [
                {'size': 'S', 'stock': 12},
                {'size': 'M', 'stock': 22},
                {'size': 'L', 'stock': 18},
                {'size': 'XL', 'stock': 14},
            ]
        },
    ]
    
    for prod_data in products_data:
        variants = prod_data.pop('variants')
        
        product, created = Product.objects.get_or_create(
            name=prod_data['name'],
            defaults=prod_data
        )
        
        if created:
            # Create variants
            for var_data in variants:
                ProductVariant.objects.get_or_create(
                    product=product,
                    size=var_data['size'],
                    defaults={'stock': var_data['stock']}
                )
    
    print(f"✓ {len(products_data)} sample products created")


def create_admin_user():
    """Create admin user if doesn't exist"""
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@malice.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        print("✓ Admin user created (username: admin, password: admin123)")
    else:
        print("✓ Admin user already exists")


def main():
    print("=" * 50)
    print("MALICE E-Commerce - Initial Data Setup")
    print("=" * 50)
    print()
    
    try:
        create_categories()
        create_sample_products()
        create_admin_user()
        
        print()
        print("=" * 50)
        print("Setup completed successfully!")
        print("=" * 50)
        print()
        print("You can now:")
        print("- Visit http://127.0.0.1:8000/ to see the store")
        print("- Login to admin at http://127.0.0.1:8000/admin/")
        print("  Username: admin")
        print("  Password: admin123")
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you've run migrations first: python manage.py migrate")


if __name__ == '__main__':
    main()
