#!/usr/bin/env python3
"""
Setup test driver with different Telegram account
"""

import os
import sys
from datetime import datetime
from app import app
from app import db
from models import Driver, Order
from complete_order_workflow import OrderWorkflowManager

def setup_test_driver():
    """Setup a test driver with different account and test notification"""
    
    with app.app_context():
        # Create or update test driver with a different Telegram ID
        test_telegram_id = 999888777  # Different test ID
        
        # Remove existing test driver if exists
        existing_driver = Driver.query.filter_by(telegram_user_id=test_telegram_id).first()
        if existing_driver:
            db.session.delete(existing_driver)
            db.session.commit()
        
        # Create new test driver
        test_driver = Driver(
            name='Test Driver - Different Account',
            phone_number='+251999888777',
            telegram_user_id=test_telegram_id,
            vehicle_type='motorcycle',
            is_active=True,
            is_available=True,
            is_approved=True,
            approval_status='approved',
            current_lat=9.148,  # Near ET-FOOD location
            current_lng=40.491,
            last_location_update=datetime.utcnow()
        )
        
        db.session.add(test_driver)
        db.session.commit()
        
        print(f"✅ Created test driver:")
        print(f"   Name: {test_driver.name}")
        print(f"   Telegram ID: {test_driver.telegram_user_id}")
        print(f"   Location: {test_driver.current_lat}, {test_driver.current_lng}")
        print(f"   Status: Active, Available, Approved")
        print()
        
        # Test notification for Order #44
        print("Testing driver notification for Order #44...")
        manager = OrderWorkflowManager()
        result = manager.find_nearby_drivers(44)
        
        if result:
            print("✅ Driver notification system working!")
            print("The system found nearby drivers and sent notifications.")
            print(f"Check logs for notification attempts to Telegram ID: {test_telegram_id}")
        else:
            print("❌ Driver notification failed")
            
        # Show all available drivers
        print("\nAll available drivers:")
        drivers = Driver.query.filter_by(is_active=True, is_available=True).all()
        for driver in drivers:
            print(f"  - {driver.name} (Telegram: {driver.telegram_user_id})")
            print(f"    Location: {driver.current_lat}, {driver.current_lng}")
            print(f"    Last update: {driver.last_location_update}")
            print()

if __name__ == "__main__":
    setup_test_driver()