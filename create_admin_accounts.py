#!/usr/bin/env python3
"""
Create admin accounts for ET-FOOD system
"""

from app import app, db
from models import AdminUser, KitchenStaff, Restaurant
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_admin_accounts():
    """Create default admin and kitchen staff accounts"""
    with app.app_context():
        # Get restaurants
        restaurants = Restaurant.query.all()
        if not restaurants:
            print("No restaurants found. Please run app.py first to create restaurants.")
            return
        
        flavour_cafe = restaurants[0]  # Flavour cafe | E.Fabrica
        
        # Create Super Admin
        super_admin = AdminUser.query.filter_by(username='admin').first()
        if not super_admin:
            super_admin = AdminUser(
                username='admin',
                email='admin@etfood.com',
                full_name='Super Administrator',
                phone='+251911000000',
                role='super_admin',
                is_active=True,
                is_approved=True,
                password_hash=generate_password_hash('admin123'),
                restaurant_id=None,  # Super admin has access to all restaurants
                permissions={'all': True}
            )
            db.session.add(super_admin)
            print("✓ Created Super Admin (admin/admin123)")
        
        # Create Restaurant Admin for Flavour Cafe
        restaurant_admin = AdminUser.query.filter_by(username='flavour').first()
        if not restaurant_admin:
            restaurant_admin = AdminUser(
                username='flavour',
                email='flavour@etfood.com',
                full_name='Flavour Cafe Manager',
                phone='+251911123456',
                role='restaurant_admin',
                is_active=True,
                is_approved=True,
                password_hash=generate_password_hash('flavour123'),
                restaurant_id=flavour_cafe.id,
                permissions={'restaurant_management': True, 'order_management': True}
            )
            db.session.add(restaurant_admin)
            print("✓ Created Restaurant Admin (flavour/flavour123)")
        
        # Create Kitchen Staff for Flavour Cafe
        kitchen_staff = KitchenStaff.query.filter_by(username='kitchen').first()
        if not kitchen_staff:
            kitchen_staff = KitchenStaff(
                name='Kitchen Manager',
                username='kitchen',
                password_hash=generate_password_hash('kitchen123'),
                phone='+251911123457',
                email='kitchen@etfood.com',
                restaurant_id=flavour_cafe.id,
                is_active=True,
                position='Head Chef',
                hire_date=datetime.utcnow()
            )
            db.session.add(kitchen_staff)
            print("✓ Created Kitchen Staff (kitchen/kitchen123)")
        
        # Create Additional Admin with simple credentials
        simple_admin = AdminUser.query.filter_by(username='superadmin').first()
        if not simple_admin:
            simple_admin = AdminUser(
                username='superadmin',
                email='superadmin@etfood.com',
                full_name='Super Admin',
                phone='+251911000001',
                role='super_admin',
                is_active=True,
                is_approved=True,
                password_hash=generate_password_hash('superadmin'),
                restaurant_id=None,
                permissions={'all': True}
            )
            db.session.add(simple_admin)
            print("✓ Created Super Admin (superadmin/superadmin)")
        
        # Commit all changes
        try:
            db.session.commit()
            print("\n🎉 All admin accounts created successfully!")
            print("\n📋 Login Credentials:")
            print("Super Admin: admin/admin123")
            print("Super Admin: superadmin/superadmin")
            print("Restaurant Admin: flavour/flavour123")
            print("Kitchen Staff: kitchen/kitchen123")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating accounts: {e}")

if __name__ == '__main__':
    create_admin_accounts()