#!/usr/bin/env python3
from app import app, db
from models import AdminUser
from werkzeug.security import generate_password_hash

with app.app_context():
    # Find the super admin user
    admin = AdminUser.query.filter_by(username='superadmin').first()
    
    if admin:
        # Generate a proper password hash for 'admin123'
        admin.password_hash = generate_password_hash('admin123')
        db.session.commit()
        print("✅ Super admin password updated successfully!")
        print("Username: superadmin")
        print("Password: admin123")
    else:
        # Create a new super admin user
        admin = AdminUser(
            username='superadmin',
            email='superadmin@etfood.com',
            password_hash=generate_password_hash('admin123'),
            role='super_admin',
            is_active=True,
            restaurant_id=None
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Super admin user created successfully!")
        print("Username: superadmin")
        print("Password: admin123")