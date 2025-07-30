#!/usr/bin/env python3
"""
Create a test driver and order to demonstrate driver bot functionality
"""

from app import app, db
from models import Driver, Order, MenuItem
import json

def create_test_driver():
    """Create a test driver for demonstration"""
    with app.app_context():
        # Check if test driver already exists
        test_driver = Driver.query.filter_by(name="Test Driver").first()
        
        if not test_driver:
            # Create test driver (you need to provide your Telegram user ID)
            test_driver = Driver(
                name="Test Driver",
                phone_number="+251-912-345-678",
                telegram_user_id=None,  # Replace with actual Telegram user ID
                vehicle_type="motorcycle",
                is_active=True,
                is_available=True,
                is_approved=True,
                approval_status="approved"
            )
            
            db.session.add(test_driver)
            db.session.commit()
            
            print(f"✅ Test driver created with ID: {test_driver.id}")
        else:
            print(f"✅ Test driver already exists with ID: {test_driver.id}")
            
        return test_driver

def create_test_order():
    """Create a test order for demonstration"""
    with app.app_context():
        # Get first menu item
        menu_item = MenuItem.query.first()
        
        if not menu_item:
            print("❌ No menu items found. Please run the app first to populate menu.")
            return None
            
        # Create test order
        test_order = Order(
            telegram_user_id=123456789,  # Mock customer ID
            customer_name="Test Customer",
            customer_phone="+251-911-987-654",
            customer_address="Test Address, Addis Ababa",
            items=json.dumps([{
                "id": menu_item.id,
                "name": menu_item.name,
                "price": menu_item.price,
                "quantity": 2
            }]),
            total_amount=menu_item.price * 2,
            payment_method="Cash on Delivery",
            status="pending",
            location_lat=9.165,
            location_lng=40.510
        )
        
        db.session.add(test_order)
        db.session.commit()
        
        print(f"✅ Test order created with ID: {test_order.id}")
        print(f"   Order: 2x {menu_item.name} = {test_order.total_amount:.2f} ETB")
        
        return test_order

if __name__ == "__main__":
    print("🔧 Creating test data for driver bot demonstration...")
    
    driver = create_test_driver()
    order = create_test_order()
    
    if driver and order:
        print(f"\n📱 To test the driver bot:")
        print(f"1. Update driver telegram_user_id to your Telegram ID")
        print(f"2. Assign order {order.id} to driver {driver.id} from admin panel")
        print(f"3. Driver will receive notification on @Food_Driver_Bot")
        print(f"4. Open driver panel mini-app to see order details")
        print(f"5. Accept/reject order to test functionality")
        
        print(f"\n🤖 Driver Bot: @Food_Driver_Bot")
        print(f"📝 Test Order ID: {order.id}")
        print(f"🚚 Test Driver ID: {driver.id}")