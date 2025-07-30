#!/usr/bin/env python3
"""
Create Admin Credentials for ET-FOOD
Creates proper admin accounts with correct passwords for restaurant management
"""

import sys
import os
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Restaurant, AdminUser

def create_admin_accounts():
    """Create admin accounts for the food delivery app"""
    with app.app_context():
        print("Creating admin accounts for ET-FOOD...")
        
        # Get Flavour cafe restaurant
        restaurant = Restaurant.query.filter_by(name='Flavour cafe | E.Fabrica').first()
        if not restaurant:
            print("Flavour cafe restaurant not found!")
            return False
        
        print(f"Found restaurant: {restaurant.name} (ID: {restaurant.id})")
        
        # Admin accounts to create
        admin_accounts = [
            {
                'username': 'admin',
                'password': 'admin123',
                'full_name': 'Admin User',
                'email': 'admin@flavourcafe.com',
                'role': 'admin',
                'restaurant_id': restaurant.id
            },
            {
                'username': 'flavour',
                'password': 'flavour123', 
                'full_name': 'Flavour Cafe Manager',
                'email': 'manager@flavourcafe.com',
                'role': 'admin',
                'restaurant_id': restaurant.id
            }
        ]
        
        created_count = 0
        
        for admin_data in admin_accounts:
            # Check if admin already exists
            existing_admin = AdminUser.query.filter_by(username=admin_data['username']).first()
            
            if existing_admin:
                print(f"Updating existing admin: {admin_data['username']}")
                # Update existing admin
                existing_admin.set_password(admin_data['password'])
                existing_admin.full_name = admin_data['full_name']
                existing_admin.email = admin_data['email']
                existing_admin.role = admin_data['role']
                existing_admin.restaurant_id = admin_data['restaurant_id']
                existing_admin.is_active = True
                existing_admin.is_approved = True
                existing_admin.updated_at = datetime.utcnow()
            else:
                print(f"Creating new admin: {admin_data['username']}")
                # Create new admin
                admin = AdminUser(
                    username=admin_data['username'],
                    full_name=admin_data['full_name'],
                    email=admin_data['email'],
                    role=admin_data['role'],
                    restaurant_id=admin_data['restaurant_id'],
                    is_active=True,
                    is_approved=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                admin.set_password(admin_data['password'])
                db.session.add(admin)
            
            created_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✅ SUCCESS: {created_count} admin accounts ready!")
        print("\n📋 Login Credentials:")
        print("1. Username: admin     | Password: admin123")
        print("2. Username: flavour   | Password: flavour123")
        print(f"\n🏪 Restaurant: {restaurant.name}")
        print("🔗 Admin Login URL: /admin")
        
        # Verify accounts
        print("\n🔍 Verification:")
        for admin_data in admin_accounts:
            admin = AdminUser.query.filter_by(username=admin_data['username']).first()
            if admin and admin.check_password(admin_data['password']):
                print(f"   ✅ {admin_data['username']} - Password verified")
            else:
                print(f"   ❌ {admin_data['username']} - Password verification failed")
        
        return True

if __name__ == "__main__":
    success = create_admin_accounts()
    if success:
        print("\n🎉 Admin credentials created successfully!")
        print("You can now log in to the admin dashboard!")
    else:
        print("\n❌ Failed to create admin credentials.")