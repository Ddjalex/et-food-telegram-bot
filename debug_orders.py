#!/usr/bin/env python3
"""
Debug script to check orders and admin data
"""

from app import app, db
from models import Order, AdminUser, Restaurant
from datetime import datetime

def debug_orders():
    """Debug orders issue"""
    with app.app_context():
        print("=== DEBUG ORDERS ===")
        
        # Check all orders
        orders = Order.query.all()
        print(f"Total orders in database: {len(orders)}")
        
        for order in orders:
            print(f"\nOrder #{order.id}:")
            print(f"  Customer: {order.customer_name}")
            print(f"  Phone: {order.customer_phone}")
            print(f"  Restaurant ID: {order.restaurant_id}")
            print(f"  Status: {order.status}")
            print(f"  Total: {order.total_amount}")
            print(f"  Created: {order.created_at}")
        
        # Check specific order by phone
        specific_order = Order.query.filter_by(customer_phone='0913720351').first()
        if specific_order:
            print(f"\nFound order for phone 0913720351:")
            print(f"  Order ID: {specific_order.id}")
            print(f"  Restaurant ID: {specific_order.restaurant_id}")
            print(f"  Status: {specific_order.status}")
        else:
            print("\nNo order found for phone 0913720351")
        
        # Check admin users
        print("\n=== ADMIN USERS ===")
        admins = AdminUser.query.all()
        for admin in admins:
            print(f"Admin ID: {admin.id}, Username: {admin.username}, Restaurant: {admin.restaurant_id}")
        
        # Check restaurants
        print("\n=== RESTAURANTS ===")
        restaurants = Restaurant.query.all()
        for restaurant in restaurants:
            print(f"Restaurant ID: {restaurant.id}, Name: {restaurant.name}")

if __name__ == "__main__":
    debug_orders()