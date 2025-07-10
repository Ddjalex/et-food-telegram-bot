#!/usr/bin/env python3
"""
Fix driver notification system and create test drivers
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models import Driver
from datetime import datetime

def create_test_driver():
    """Create a test driver for notification testing"""
    with app.app_context():
        # Check if DJ ALEX already exists
        existing_driver = Driver.query.filter_by(name="DJ ALEX").first()
        
        if not existing_driver:
            # Create DJ ALEX test driver
            driver = Driver(
                name="DJ ALEX",
                phone_number="+251911234567",
                telegram_user_id=383870190,  # This should be different from admin
                vehicle_type="motorcycle",
                is_active=True,
                is_available=True,
                is_approved=True,
                approval_status='approved',
                current_lat=9.0579,  # Addis Ababa coordinates
                current_lng=38.7914,
                last_location_update=datetime.utcnow()
            )
            
            db.session.add(driver)
            db.session.commit()
            print(f"✅ Created test driver: {driver.name} (ID: {driver.id})")
        else:
            # Update existing driver to be available
            existing_driver.is_active = True
            existing_driver.is_available = True  
            existing_driver.is_approved = True
            existing_driver.approval_status = 'approved'
            existing_driver.current_lat = 9.0579
            existing_driver.current_lng = 38.7914
            existing_driver.last_location_update = datetime.utcnow()
            
            db.session.commit()
            print(f"✅ Updated existing driver: {existing_driver.name} (ID: {existing_driver.id}) - Set to AVAILABLE")

if __name__ == "__main__":
    create_test_driver()