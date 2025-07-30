#!/usr/bin/env python3
"""
Check current driver status
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from app import db
from models import Driver

def check_drivers():
    """Check current driver status"""
    with app.app_context():
        drivers = Driver.query.all()
        
        print("Current Drivers in Database:")
        print("=" * 50)
        
        if not drivers:
            print("❌ No drivers found in database")
            return
        
        for driver in drivers:
            print(f"Driver ID: {driver.id}")
            print(f"Name: {driver.name}")
            print(f"Phone: {driver.phone_number}")
            print(f"Telegram ID: {driver.telegram_user_id}")
            print(f"Is Active: {driver.is_active}")
            print(f"Is Available: {driver.is_available}")
            print(f"Is Approved: {driver.is_approved}")
            print(f"Approval Status: {driver.approval_status}")
            print(f"Vehicle Type: {driver.vehicle_type}")
            print(f"Location: {driver.current_lat}, {driver.current_lng}")
            print(f"Last Location Update: {driver.last_location_update}")
            print("-" * 30)

if __name__ == "__main__":
    check_drivers()