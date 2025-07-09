#!/usr/bin/env python3
"""
Fix pending drivers with missing data
"""

import os
import sys
from app import app
from extensions import db
from models import Driver

def fix_pending_drivers():
    """Fix drivers with missing required fields"""
    
    with app.app_context():
        # Find drivers with missing data
        drivers_to_fix = Driver.query.filter(
            (Driver.name.is_(None)) | 
            (Driver.phone_number.is_(None))
        ).all()
        
        print(f"Found {len(drivers_to_fix)} drivers to fix")
        
        for driver in drivers_to_fix:
            print(f"Fixing driver ID {driver.id}")
            
            # Fix missing name
            if not driver.name:
                driver.name = f"Driver {driver.id}"
                
            # Fix missing phone number  
            if not driver.phone_number:
                driver.phone_number = "+251900000000"
                
            # Ensure proper approval status
            if not driver.approval_status:
                driver.approval_status = 'pending'
                driver.is_approved = False
                driver.is_available = False
                
        db.session.commit()
        print("✅ Fixed all pending drivers")
        
        # Show all pending drivers
        pending_drivers = Driver.query.filter_by(approval_status='pending').all()
        print(f"\nPending drivers for admin approval: {len(pending_drivers)}")
        for driver in pending_drivers:
            print(f"  - {driver.name} (ID: {driver.id}, Telegram: {driver.telegram_user_id})")

if __name__ == "__main__":
    fix_pending_drivers()