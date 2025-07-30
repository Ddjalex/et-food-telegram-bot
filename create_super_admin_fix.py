#!/usr/bin/env python3
"""Create a super admin user for testing driver deletion"""

from app import app, db
from models import AdminUser
from werkzeug.security import generate_password_hash

def create_super_admin():
    with app.app_context():
        # Check if super admin already exists
        existing_super_admin = AdminUser.query.filter_by(role='super_admin').first()
        
        if existing_super_admin:
            print(f"Super admin already exists: {existing_super_admin.username}")
            print(f"Password can be reset if needed")
            return existing_super_admin
        
        # Create new super admin
        super_admin = AdminUser(
            username='superadmin',
            password_hash=generate_password_hash('admin123'),
            role='super_admin',
            full_name='Super Administrator',
            email='admin@etfood.com',
            is_active=True,
            is_approved=True
        )
        
        try:
            db.session.add(super_admin)
            db.session.commit()
            print(f"Super admin created successfully!")
            print(f"Username: superadmin")
            print(f"Password: admin123")
            print(f"Login URL: /superadmin/login")
            return super_admin
        except Exception as e:
            db.session.rollback()
            print(f"Error creating super admin: {e}")
            return None

if __name__ == '__main__':
    create_super_admin()