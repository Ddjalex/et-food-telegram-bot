#!/usr/bin/env python3
"""
Real driver registration system for BeUdelivery-like integration
Creates a proper driver onboarding flow with real Telegram integration
"""

import os
from datetime import datetime
from app import app
from app import db
from models import Driver, AdminUser

def create_real_driver_system():
    """Create real driver registration system"""
    
    with app.app_context():
        # Create admin user if not exists
        admin = AdminUser.query.filter_by(telegram_user_id=383870190).first()
        if not admin:
            admin = AdminUser(
                telegram_user_id=383870190,  # Your Telegram ID
                username="admin",
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Created admin user: {admin.username}")
        
        # Update test drivers to use real Telegram IDs for testing
        # In real deployment, these would be actual driver Telegram IDs
        test_drivers = [
            {
                'name': 'Real Driver 1',
                'phone_number': '+251911000001',
                'telegram_user_id': 383870190,  # Use your Telegram ID for testing
                'vehicle_type': 'motorcycle',
                'is_active': True,
                'is_available': True,
                'is_approved': True,
                'approval_status': 'approved',
                'current_lat': 9.150,
                'current_lng': 40.492,
                'last_location_update': datetime.utcnow()
            }
        ]
        
        # Remove old test drivers
        Driver.query.filter(Driver.name.like('Test Driver%')).delete()
        
        # Add real driver for testing
        for driver_data in test_drivers:
            existing = Driver.query.filter_by(telegram_user_id=driver_data['telegram_user_id']).first()
            if not existing:
                driver = Driver(**driver_data)
                db.session.add(driver)
                print(f"✅ Created real driver: {driver.name}")
        
        db.session.commit()
        
        print("\n🚀 Real driver system created!")
        print("📱 To test driver notifications:")
        print("1. Start the driver bot in Telegram")
        print("2. Send /start to the driver bot")
        print("3. Place a test order")
        print("4. You should receive driver notifications!")

if __name__ == "__main__":
    create_real_driver_system()