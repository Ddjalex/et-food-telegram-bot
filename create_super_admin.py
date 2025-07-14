"""
Create a super admin user for testing the multi-tier admin system
"""
from app import app, db
from models import AdminUser
from werkzeug.security import generate_password_hash

def create_super_admin():
    """Create a super admin user"""
    with app.app_context():
        # Check if super admin already exists
        existing_super_admin = AdminUser.query.filter_by(role='super_admin').first()
        if existing_super_admin:
            print(f"Super admin already exists: {existing_super_admin.username}")
            return
        
        # Create super admin
        super_admin = AdminUser(
            username='superadmin',
            email='superadmin@etfood.com',
            full_name='Super Administrator',
            phone='+251911000000',
            role='super_admin',
            password_hash=generate_password_hash('superadmin123'),
            is_active=True,
            is_blocked=False,
            permissions={
                'can_create_admins': True,
                'can_delete_admins': True,
                'can_manage_restaurants': True,
                'can_view_analytics': True,
                'can_manage_system': True
            }
        )
        
        db.session.add(super_admin)
        db.session.commit()
        
        print("Super admin created successfully!")
        print(f"Username: {super_admin.username}")
        print(f"Password: superadmin123")
        print(f"Role: {super_admin.role}")
        print(f"Email: {super_admin.email}")
        print("\nYou can now login to the admin panel at /admin/login")

if __name__ == "__main__":
    create_super_admin()