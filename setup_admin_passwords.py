#!/usr/bin/env python3
"""
Setup Admin Users and Passwords
This script creates admin users with default passwords that can be changed later
"""

from app import app
from app import db
from models import AdminUser
from werkzeug.security import generate_password_hash

def setup_admin_users():
    """Setup admin users with default passwords"""
    with app.app_context():
        # Check if super admin exists
        super_admin = AdminUser.query.filter_by(username='superadmin', role='super_admin').first()
        if not super_admin:
            super_admin = AdminUser(
                username='superadmin',
                full_name='Super Administrator',
                email='superadmin@etfood.com',
                role='super_admin',
                is_active=True,
                is_blocked=False
            )
            super_admin.set_password('admin123')  # Default password
            db.session.add(super_admin)
            print("✓ Created super admin: username='superadmin', password='admin123'")
        else:
            print("✓ Super admin already exists")

        # Check if restaurant admin exists
        admin = AdminUser.query.filter_by(username='admin', role='admin').first()
        if not admin:
            admin = AdminUser(
                username='admin',
                full_name='Restaurant Administrator',
                email='admin@etfood.com',
                role='admin',
                restaurant_id=1,
                is_active=True,
                is_blocked=False
            )
            admin.set_password('admin123')  # Default password
            db.session.add(admin)
            print("✓ Created restaurant admin: username='admin', password='admin123'")
        else:
            print("✓ Restaurant admin already exists")

        # Check if kitchen staff exists (managed through restaurant admin)
        kitchen = AdminUser.query.filter_by(username='kitchen', role='kitchen_staff').first()
        if not kitchen:
            kitchen = AdminUser(
                username='kitchen',
                full_name='Kitchen Staff',
                email='kitchen@etfood.com',
                role='kitchen_staff',
                restaurant_id=1,
                is_active=True,
                is_blocked=False
            )
            kitchen.set_password('kitchen123')  # Default password
            db.session.add(kitchen)
            print("✓ Created kitchen staff: username='kitchen', password='kitchen123'")
            print("✓ Note: Kitchen staff is managed through restaurant admin at /admin")
        else:
            print("✓ Kitchen staff already exists")

        db.session.commit()
        print("\n" + "="*50)
        print("CURRENT LOGIN CREDENTIALS:")
        print("="*50)
        print("Super Admin Login (/superadmin):")
        print("  Username: superadmin")
        print("  Password: admin123")
        print()
        print("Restaurant Admin Login (/admin):")
        print("  Username: admin") 
        print("  Password: admin123")
        print()
        print("Kitchen Staff (managed by Restaurant Admin):")
        print("  Access through: /admin")
        print("  Note: Kitchen staff is managed through restaurant admin dashboard")
        print("="*50)

if __name__ == '__main__':
    setup_admin_users()