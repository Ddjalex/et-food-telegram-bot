#!/usr/bin/env python3
"""
Create test data for kitchen driver notification system
"""

import json
from datetime import datetime, timedelta
from app import app
from app import db
from models import Order, Driver, AdminUser

def create_test_order():
    """Create a test order for testing"""
    print("📝 Creating test order...")
    
    with app.app_context():
        # Create a test order
        order = Order(
            customer_name="John Doe",
            customer_phone="+251912345678",
            customer_address="Bole, Addis Ababa, Ethiopia",
            telegram_user_id="123456789",
            payment_method="cash",
            total_amount=250.00,
            status="confirmed",
            items=[
                {
                    "name": "Chicken Burger",
                    "price": 150.00,
                    "quantity": 1
                },
                {
                    "name": "French Fries",
                    "price": 50.00,
                    "quantity": 2
                }
            ],
            location_lat=9.047658,
            location_lng=38.741143,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(order)
        db.session.commit()
        
        print(f"✅ Created test order #{order.id}")
        return order.id

def create_test_driver():
    """Create a test driver for testing"""
    print("👤 Creating test driver...")
    
    with app.app_context():
        # Create a test driver
        driver = Driver(
            name="Test Driver",
            phone_number="+251911223344",
            telegram_user_id="383870190",
            vehicle_type="motorcycle",
            is_active=True,
            is_available=True,
            is_approved=True,
            current_lat=9.042000,
            current_lng=38.738000,
            last_location_update=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        db.session.add(driver)
        db.session.commit()
        
        print(f"✅ Created test driver #{driver.id}")
        return driver.id

def create_admin_user():
    """Create admin user for testing"""
    print("👨‍💼 Creating admin user...")
    
    with app.app_context():
        # Check if admin already exists
        admin = AdminUser.query.filter_by(username="admin").first()
        if admin:
            print("✅ Admin user already exists")
            return admin.id
        
        # Create admin user
        admin = AdminUser(
            username="admin",
            telegram_user_id="383870191",
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"✅ Created admin user #{admin.id}")
        return admin.id

if __name__ == "__main__":
    print("🚀 Creating test data for kitchen driver notification system")
    print("=" * 60)
    
    try:
        # Create test data
        admin_id = create_admin_user()
        driver_id = create_test_driver()
        order_id = create_test_order()
        
        print("\n✅ Test data created successfully!")
        print(f"   Admin ID: {admin_id}")
        print(f"   Driver ID: {driver_id}")
        print(f"   Order ID: {order_id}")
        
        print("\n📝 To test the system:")
        print("1. Run: python test_kitchen_driver_notification.py")
        print("2. Or go to kitchen dashboard and click 'Prepare' on the order")
        print("3. Check if driver receives notification")
        
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()