#!/usr/bin/env python3
"""
Create test drivers to verify the driver management system
"""

from app import app, db
from models import Driver
from datetime import datetime

def create_test_drivers():
    """Create test drivers with proper field names"""
    with app.app_context():
        # Clear existing drivers
        Driver.query.delete()
        
        # Create test drivers
        drivers = [
            Driver(
                name="John Doe",
                phone_number="+251911234567",
                vehicle_type="motorcycle",
                is_active=True,
                is_available=True,
                approval_status="approved",
                is_approved=True,
                current_lat=9.0200,
                current_lng=38.7400,
                last_location_update=datetime.utcnow()
            ),
            Driver(
                name="Jane Smith",
                phone_number="+251922345678",
                vehicle_type="car",
                is_active=True,
                is_available=False,
                approval_status="approved",
                is_approved=True,
                current_lat=9.0300,
                current_lng=38.7500,
                last_location_update=datetime.utcnow()
            ),
            Driver(
                name="Mike Johnson",
                phone_number="+251933456789",
                vehicle_type="bicycle",
                is_active=False,
                is_available=True,
                approval_status="pending",
                is_approved=False
            )
        ]
        
        for driver in drivers:
            db.session.add(driver)
        
        db.session.commit()
        print(f"Created {len(drivers)} test drivers successfully!")

if __name__ == "__main__":
    create_test_drivers()