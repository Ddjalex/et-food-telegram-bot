#!/usr/bin/env python3
"""
Fix all drivers to be available for testing
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from app import db
from models import Driver
from datetime import datetime

def fix_all_drivers():
    """Set all drivers to available status"""
    with app.app_context():
        drivers = Driver.query.all()
        
        for driver in drivers:
            driver.is_active = True
            driver.is_available = True
            driver.is_approved = True
            driver.approval_status = 'approved'
            driver.last_location_update = datetime.utcnow()
            
            # Update location to Addis Ababa area if not set
            if not driver.current_lat or not driver.current_lng:
                driver.current_lat = 9.0579
                driver.current_lng = 38.7914
            
            print(f"✅ Updated driver: {driver.name} - Set to AVAILABLE")
        
        db.session.commit()
        print(f"\n✅ All {len(drivers)} drivers are now AVAILABLE for order assignments")

if __name__ == "__main__":
    fix_all_drivers()