#!/usr/bin/env python3
"""
Fix Super Admin User Creation and Database Issues
"""
import os
import sys
from app import app, db
from models import AdminUser
from werkzeug.security import generate_password_hash

def create_super_admin():
    """Create or update super admin user"""
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            
            # Check if super admin already exists
            super_admin = AdminUser.query.filter_by(username='superadmin').first()
            
            if super_admin:
                print("Super admin already exists, updating...")
                # Update existing super admin
                super_admin.password_hash = generate_password_hash('admin123')
                super_admin.role = 'super_admin'
                super_admin.is_active = True
                super_admin.is_blocked = False
                super_admin.full_name = 'Super Administrator'
                super_admin.email = 'admin@etfood.com'
            else:
                print("Creating new super admin...")
                # Create new super admin
                super_admin = AdminUser(
                    username='superadmin',
                    password_hash=generate_password_hash('admin123'),
                    full_name='Super Administrator',
                    email='admin@etfood.com',
                    role='super_admin',
                    is_active=True,
                    is_blocked=False
                )
                db.session.add(super_admin)
            
            db.session.commit()
            print("✅ Super admin created/updated successfully!")
            print("   Username: superadmin")
            print("   Password: admin123")
            print("   Role: super_admin")
            
            # Verify the user was created
            verify_admin = AdminUser.query.filter_by(username='superadmin').first()
            if verify_admin:
                print(f"✅ Verification successful - Admin ID: {verify_admin.id}")
                print(f"   Active: {verify_admin.is_active}")
                print(f"   Blocked: {verify_admin.is_blocked}")
                print(f"   Role: {verify_admin.role}")
            else:
                print("❌ Verification failed - Admin not found")
                
        except Exception as e:
            print(f"❌ Error creating super admin: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_super_admin()