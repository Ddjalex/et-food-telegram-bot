#!/usr/bin/env python3
"""
Create a new test order to trigger driver notifications
"""

import os
import sys
from datetime import datetime
from app import app
from app import db
from models import Order
from complete_order_workflow import process_new_order

def create_test_order():
    """Create a new test order and trigger driver notifications"""
    
    with app.app_context():
        # Create new test order
        test_order = Order(
            telegram_user_id=123456789,  # Test customer ID
            customer_name='Test Customer',
            customer_phone='+251900000000',
            customer_address='Test Address, Addis Ababa',
            items=[{
                'id': 1,
                'name': 'Beef Burger Normal',
                'price': 400,
                'quantity': 1,
                'total': 400
            }],
            total_amount=400.0,
            payment_method='cash',
            location_lat=9.150,  # Test location near drivers
            location_lng=40.490
        )
        
        db.session.add(test_order)
        db.session.commit()
        
        print(f"✅ Created test order #{test_order.id}")
        print(f"   Customer: {test_order.customer_name}")
        print(f"   Location: {test_order.location_lat}, {test_order.location_lng}")
        print(f"   Total: {test_order.total_amount} ETB")
        print()
        
        # Trigger driver notification workflow
        print("Triggering automatic driver notification...")
        process_new_order(test_order.id)
        
        print(f"✅ Driver notification triggered for Order #{test_order.id}")
        print("Check the logs above for notification details")
        
        return test_order.id

if __name__ == "__main__":
    order_id = create_test_order()
    print(f"\nNew test order created: #{order_id}")