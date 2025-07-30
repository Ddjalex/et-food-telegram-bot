#!/usr/bin/env python3
"""
Reset the Flavor admin password to a known value
"""
from app import app, db
from models import AdminUser
from werkzeug.security import generate_password_hash

def reset_flavor_admin_password():
    """Reset the Flavor admin password"""
    with app.app_context():
        # Find the Flavor admin
        admin = AdminUser.query.filter_by(username='Flavor', restaurant_id=1).first()
        
        if not admin:
            print("❌ Flavor admin not found!")
            return False
        
        # Set a known password
        new_password = "admin123"
        admin.password_hash = generate_password_hash(new_password)
        admin.is_active = True  # Ensure account is active
        
        db.session.commit()
        
        print("✅ Flavor admin password reset successfully!")
        print(f"Username: {admin.username}")
        print(f"Password: {new_password}")
        print(f"Restaurant: {admin.restaurant_id} (Flavour cafe)")
        print(f"Role: {admin.role}")
        print(f"Active: {admin.is_active}")
        
        return True

if __name__ == "__main__":
    reset_flavor_admin_password()