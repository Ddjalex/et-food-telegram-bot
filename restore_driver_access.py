#!/usr/bin/env python3

"""
Restore driver management access for all restaurant admins
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import AdminUser, Restaurant, db

def restore_driver_access():
    with app.app_context():
        print("=== Restoring Driver Management Access ===")
        
        # Give driver management access to ALL restaurant admins
        admins = AdminUser.query.filter_by(role='admin').all()
        
        for admin in admins:
            restaurant_name = "None"
            if admin.restaurant_id:
                restaurant = Restaurant.query.get(admin.restaurant_id)
                restaurant_name = restaurant.name if restaurant else f"ID:{admin.restaurant_id}"
            
            admin.is_approved = True
            print(f"✓ Granted driver management access to {restaurant_name} ({admin.username})")
        
        db.session.commit()
        
        print("\n=== Final Status - All Restaurants Have Driver Management ===")
        admins = AdminUser.query.filter_by(role='admin').all()
        
        for admin in admins:
            restaurant_name = "None"
            if admin.restaurant_id:
                restaurant = Restaurant.query.get(admin.restaurant_id)
                restaurant_name = restaurant.name if restaurant else f"ID:{admin.restaurant_id}"
            
            print(f"- {restaurant_name}: DRIVER MANAGEMENT ENABLED")

if __name__ == "__main__":
    restore_driver_access()