#!/usr/bin/env python3

"""
Quick script to check admin approval status
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import AdminUser, Restaurant

def check_admin_approval():
    with app.app_context():
        print("=== Admin Users and Approval Status ===")
        admins = AdminUser.query.filter_by(role='admin').all()
        
        for admin in admins:
            restaurant_name = "None"
            if admin.restaurant_id:
                restaurant = Restaurant.query.get(admin.restaurant_id)
                restaurant_name = restaurant.name if restaurant else f"ID:{admin.restaurant_id}"
            
            approval_status = "✓ APPROVED" if admin.is_approved else "✗ NOT APPROVED"
            
            print(f"ID: {admin.id}")
            print(f"Username: {admin.username}")
            print(f"Restaurant: {restaurant_name}")
            print(f"Approval Status: {approval_status}")
            print("---")
        
        print("\n=== Restaurants ===")
        restaurants = Restaurant.query.all()
        for restaurant in restaurants:
            print(f"ID: {restaurant.id} - Name: {restaurant.name}")
        
        # Check if we need to approve any restaurant admins
        unapproved_admins = AdminUser.query.filter_by(role='admin', is_approved=False).all()
        if unapproved_admins:
            print(f"\n⚠️  Found {len(unapproved_admins)} unapproved restaurant admins!")
            for admin in unapproved_admins:
                print(f"  - {admin.username} (Restaurant ID: {admin.restaurant_id})")
        else:
            print("\n✓ All restaurant admins are approved!")

if __name__ == "__main__":
    check_admin_approval()