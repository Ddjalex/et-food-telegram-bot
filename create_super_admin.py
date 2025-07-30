#!/usr/bin/env python3
"""
Create super admin user for login access
"""

from app import app
from app import db
from models import AdminUser
from werkzeug.security import generate_password_hash

def create_super_admin():
    """Create super admin user"""
    
    with app.app_context():
        print("🔐 Creating super admin user...")
        
        # Check if super admin already exists
        existing_admin = AdminUser.query.filter_by(username='admin').first()
        if existing_admin:
            print("⚠️  Super admin 'admin' already exists, updating password...")
            existing_admin.password_hash = generate_password_hash('admin123')
            existing_admin.role = 'super_admin'
            existing_admin.is_active = True
            existing_admin.is_approved = True
            db.session.commit()
            print("✅ Updated existing super admin password to 'admin123'")
            return
        
        # Create new super admin
        super_admin = AdminUser(
            username='admin',
            email='admin@etfood.com',
            full_name='Super Administrator',
            password_hash=generate_password_hash('admin123'),
            role='super_admin',
            is_active=True,
            is_approved=True,
            restaurant_id=None  # Super admin not tied to specific restaurant
        )
        
        db.session.add(super_admin)
        db.session.commit()
        
        print("✅ Super admin created successfully!")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Role: super_admin")
        
        # Also create backup admin
        backup_admin = AdminUser(
            username='superadmin',
            email='superadmin@etfood.com', 
            full_name='Backup Super Admin',
            password_hash=generate_password_hash('superadmin123'),
            role='super_admin',
            is_active=True,
            is_approved=True,
            restaurant_id=None
        )
        
        db.session.add(backup_admin)
        db.session.commit()
        
        print("✅ Backup super admin created!")
        print("   Username: superadmin")
        print("   Password: superadmin123")

if __name__ == '__main__':
    create_super_admin()