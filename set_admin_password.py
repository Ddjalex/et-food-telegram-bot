#!/usr/bin/env python3
"""
Set password for admin users
"""
import os
import sys
from app import app, db
from models import AdminUser, Restaurant
from werkzeug.security import generate_password_hash

def set_admin_password(username, new_password):
    """Set password for an admin user"""
    with app.app_context():
        try:
            admin = AdminUser.query.filter_by(username=username).first()
            
            if not admin:
                print(f"❌ Admin user '{username}' not found")
                return False
            
            # Set new password
            admin.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # Get restaurant info
            restaurant = Restaurant.query.filter_by(id=admin.restaurant_id).first()
            restaurant_name = restaurant.name if restaurant else "No restaurant"
            
            print(f"✅ Password updated for admin user:")
            print(f"   Username: {admin.username}")
            print(f"   Full Name: {admin.full_name}")
            print(f"   Email: {admin.email}")
            print(f"   Restaurant: {restaurant_name}")
            print(f"   Role: {admin.role}")
            print(f"   New Password: {new_password}")
            print(f"   Active: {admin.is_active}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error setting password: {e}")
            db.session.rollback()
            return False

def list_admins():
    """List all admin users"""
    with app.app_context():
        try:
            admins = AdminUser.query.filter_by(role='admin').all()
            
            print("📋 Current Admin Users:")
            print("-" * 60)
            
            for admin in admins:
                restaurant = Restaurant.query.filter_by(id=admin.restaurant_id).first()
                restaurant_name = restaurant.name if restaurant else "No restaurant"
                
                print(f"Username: {admin.username}")
                print(f"Full Name: {admin.full_name}")
                print(f"Email: {admin.email}")
                print(f"Restaurant: {restaurant_name}")
                print(f"Active: {admin.is_active}")
                print("-" * 30)
                
        except Exception as e:
            print(f"❌ Error listing admins: {e}")

if __name__ == '__main__':
    print("🔐 Admin Password Manager")
    print("=" * 50)
    
    # List current admins
    list_admins()
    
    # Set default passwords for common admin users
    print("\n🔧 Setting default passwords...")
    
    # Set password for MELKE (if exists)
    set_admin_password("MELKE", "admin123")
    
    # Set password for man (if exists)  
    set_admin_password("man", "admin123")
    
    # Set password for ADDISU (if exists)
    set_admin_password("ADDISU", "admin123")
    
    # Set password for alex (if exists)
    set_admin_password("alex", "admin123")
    
    print("\n✅ Default password 'admin123' set for all existing admin users")
    print("\n📝 To access X Factory admin dashboard:")
    print("1. Go to: /admin/login")
    print("2. Use any of the admin usernames above")
    print("3. Password: admin123")