#!/usr/bin/env python3
"""
Create test drivers for notification system testing
"""

from app import app, db
from models import Driver
from datetime import datetime

def create_test_drivers():
    """Create test drivers with proper location data for real-time notifications"""
    
    # Test driver data with different locations around Addis Ababa
    test_drivers = [
        {
            'name': 'አበበ መኮንን (Abebe Mekonnen)',
            'phone_number': '+251911123456',
            'telegram_user_id': 5753181035,  # Real user ID that has started driver bot
            'vehicle_type': 'motorcycle',
            'is_active': True,
            'is_available': True,
            'is_approved': True,
            'approval_status': 'approved',
            'current_lat': 9.045000,  # Near Bole area
            'current_lng': 38.740000,
            'last_location_update': datetime.utcnow()
        },
        {
            'name': 'ብርሃነ ተስፋዩ (Birhane Tesfayu)',
            'phone_number': '+251911234567',
            'telegram_user_id': 1234567890,  # Test ID
            'vehicle_type': 'car',
            'is_active': True,
            'is_available': True,
            'is_approved': True,
            'approval_status': 'approved',
            'current_lat': 9.050000,  # Near Piazza area
            'current_lng': 38.745000,
            'last_location_update': datetime.utcnow()
        },
        {
            'name': 'ደረጀ አልemu (Dereje Alemu)',
            'phone_number': '+251911345678',
            'telegram_user_id': 2345678901,  # Test ID
            'vehicle_type': 'bicycle',
            'is_active': True,
            'is_available': True,
            'is_approved': True,
            'approval_status': 'approved',
            'current_lat': 9.040000,  # Near Merkato area
            'current_lng': 38.735000,
            'last_location_update': datetime.utcnow()
        }
    ]
    
    # Delete existing test drivers to avoid duplicates
    Driver.query.filter(Driver.phone_number.in_([d['phone_number'] for d in test_drivers])).delete()
    db.session.commit()
    
    # Create new test drivers
    for driver_data in test_drivers:
        driver = Driver(**driver_data)
        db.session.add(driver)
        print(f"✅ Created driver: {driver_data['name']} - {driver_data['phone_number']}")
    
    db.session.commit()
    print(f"\n🎉 Successfully created {len(test_drivers)} test drivers!")
    
    # Show current drivers
    drivers = Driver.query.filter_by(is_approved=True, is_available=True).all()
    print(f"\n📋 Available drivers for notifications:")
    for driver in drivers:
        print(f"   • {driver.name} (ID: {driver.telegram_user_id}) - Location: {driver.current_lat}, {driver.current_lng}")

if __name__ == '__main__':
    with app.app_context():
        create_test_drivers()