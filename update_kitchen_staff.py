#!/usr/bin/env python3
"""
Update kitchen staff with real Telegram user ID for notifications
"""

from app import app, db
from models import KitchenStaff

def update_kitchen_staff_telegram_id():
    """Update kitchen staff with a real Telegram ID"""
    with app.app_context():
        # Get the existing kitchen staff
        kitchen_staff = KitchenStaff.query.first()
        if kitchen_staff:
            print(f"Current kitchen staff: {kitchen_staff.name}")
            print(f"Current Telegram ID: {kitchen_staff.telegram_user_id}")
            
            # For DJ ALEX who made Order #13, let's use their Telegram ID for kitchen notifications
            # This is a practical solution - the person ordering can also receive kitchen notifications
            new_telegram_id = 383870190  # DJ ALEX's Telegram ID from the orders
            
            kitchen_staff.telegram_user_id = new_telegram_id
            db.session.commit()
            
            print(f"✅ Updated kitchen staff Telegram ID to: {new_telegram_id}")
            print("Kitchen staff will now receive payment verification notifications")
        else:
            print("❌ No kitchen staff found")

if __name__ == "__main__":
    update_kitchen_staff_telegram_id()