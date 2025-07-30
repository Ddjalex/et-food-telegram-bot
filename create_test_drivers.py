#!/usr/bin/env python3
"""
Script to create test drivers with proper location data and Telegram IDs
"""

import os
import sys
from datetime import datetime, timedelta
from app import app
from app import db
from models import Driver

def create_test_drivers():
    """Create test drivers with location data for testing"""
    
    with app.app_context():
        # Remove existing test drivers
        Driver.query.filter(Driver.name.like('Test Driver%')).delete()
        db.session.commit()
        
        # Create test drivers with different locations around Addis Ababa
        test_drivers = [
            {
                'name': 'Test Driver 1',
                'phone_number': '+251911111111',
                'telegram_user_id': 123456001,  # You can change this to real Telegram IDs
                'vehicle_type': 'motorcycle',
                'is_active': True,
                'is_available': True,
                'is_approved': True,
                'approval_status': 'approved',
                'current_lat': 9.150,  # Near Bole area
                'current_lng': 40.492,
                'last_location_update': datetime.utcnow()
            },
            {
                'name': 'Test Driver 2',
                'phone_number': '+251911111112',
                'telegram_user_id': 123456002,
                'vehicle_type': 'car',
                'is_active': True,
                'is_available': True,
                'is_approved': True,
                'approval_status': 'approved',
                'current_lat': 9.155,  # Near Kazanchis
                'current_lng': 40.485,
                'last_location_update': datetime.utcnow()
            },
            {
                'name': 'Test Driver 3',
                'phone_number': '+251911111113',
                'telegram_user_id': 123456003,
                'vehicle_type': 'bicycle',
                'is_active': True,
                'is_available': True,
                'is_approved': True,
                'approval_status': 'approved',
                'current_lat': 9.140,  # Near Megenagna
                'current_lng': 40.495,
                'last_location_update': datetime.utcnow()
            }
        ]
        
        created_drivers = []
        for driver_data in test_drivers:
            driver = Driver(**driver_data)
            db.session.add(driver)
            created_drivers.append(driver)
        
        db.session.commit()
        
        print(f"✅ Created {len(created_drivers)} test drivers:")
        for driver in created_drivers:
            print(f"  - {driver.name} (ID: {driver.id}, Telegram: {driver.telegram_user_id})")
            print(f"    Location: {driver.current_lat}, {driver.current_lng}")
            print(f"    Vehicle: {driver.vehicle_type}")
            print()

def update_driver_locations():
    """Update existing drivers with current location data"""
    with app.app_context():
        # Update all existing drivers to have recent location updates
        existing_drivers = Driver.query.filter_by(is_active=True).all()
        
        for i, driver in enumerate(existing_drivers):
            if not driver.current_lat:
                # Give them locations around Addis Ababa
                base_lat = 9.145
                base_lng = 40.489
                
                # Spread drivers around the city
                offset_lat = (i * 0.01) - 0.02
                offset_lng = (i * 0.01) - 0.02
                
                driver.current_lat = base_lat + offset_lat
                driver.current_lng = base_lng + offset_lng
                driver.last_location_update = datetime.utcnow()
                
                print(f"Updated location for {driver.name}: {driver.current_lat}, {driver.current_lng}")
        
        db.session.commit()
        print(f"✅ Updated locations for {len(existing_drivers)} existing drivers")

if __name__ == "__main__":
    create_test_drivers()
    update_driver_locations()