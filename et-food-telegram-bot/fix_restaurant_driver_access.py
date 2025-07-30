#!/usr/bin/env python3

"""
Fix restaurant driver management access - only specific restaurants should have it
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import AdminUser, Restaurant, db

def fix_driver_access():
    with app.app_context():
        print("=== Current Restaurant Admins ===")
        admins = AdminUser.query.filter_by(role='admin').all()
        
        for admin in admins:
            restaurant_name = "None"
            if admin.restaurant_id:
                restaurant = Restaurant.query.get(admin.restaurant_id)
                restaurant_name = restaurant.name if restaurant else f"ID:{admin.restaurant_id}"
            
            print(f"ID: {admin.id}, Username: {admin.username}, Restaurant: {restaurant_name}, Approved: {admin.is_approved}")
        
        print("\n=== Fixing Driver Management Access ===")
        
        # Only "Flavour cafe | E.Fabrica" should have driver management
        # Rich Cafe should NOT have driver management
        
        # Get Rich Cafe admin (Babi) and revoke driver management access
        rich_cafe_admin = AdminUser.query.filter_by(username='Babi').first()
        if rich_cafe_admin:
            rich_cafe_admin.is_approved = False
            print(f"✗ Removed driver management access from Rich Cafe (Babi)")
        
        # Ensure Flavour cafe admin (Flavor) has driver management access
        flavour_cafe_admin = AdminUser.query.filter_by(username='Flavor').first()
        if flavour_cafe_admin:
            flavour_cafe_admin.is_approved = True
            print(f"✓ Confirmed driver management access for Flavour cafe (Flavor)")
        
        db.session.commit()
        
        print("\n=== Updated Status ===")
        admins = AdminUser.query.filter_by(role='admin').all()
        
        for admin in admins:
            restaurant_name = "None"
            if admin.restaurant_id:
                restaurant = Restaurant.query.get(admin.restaurant_id)
                restaurant_name = restaurant.name if restaurant else f"ID:{admin.restaurant_id}"
            
            driver_access = "HAS DRIVER MANAGEMENT" if admin.is_approved else "NO DRIVER MANAGEMENT"
            print(f"- {restaurant_name}: {driver_access}")

if __name__ == "__main__":
    fix_driver_access()