#!/usr/bin/env python3
"""
Create kitchen staff user for testing the kitchen food management system
"""

from app import app, db
from models import AdminUser
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_kitchen_staff():
    with app.app_context():
        # Check if kitchen staff already exists
        existing_kitchen = AdminUser.query.filter_by(username='kitchen').first()
        if existing_kitchen:
            print("Kitchen staff user already exists!")
            print(f"Username: kitchen")
            print(f"Password: kitchen123")
            print(f"Role: {existing_kitchen.role}")
            return
        
        # Create kitchen staff user
        kitchen_staff = AdminUser(
            username='kitchen',
            password_hash=generate_password_hash('kitchen123'),
            role='kitchen_staff',
            is_active=True,
            created_at=datetime.utcnow(),
            last_login=None
        )
        
        try:
            db.session.add(kitchen_staff)
            db.session.commit()
            print("✅ Kitchen staff user created successfully!")
            print(f"Username: kitchen")
            print(f"Password: kitchen123")
            print(f"Role: kitchen_staff")
            print("\nYou can now access the kitchen food management system at:")
            print("http://localhost:5000/kitchen/login")
        except Exception as e:
            print(f"❌ Error creating kitchen staff user: {e}")
            db.session.rollback()

if __name__ == '__main__':
    create_kitchen_staff()