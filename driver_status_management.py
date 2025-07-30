#!/usr/bin/env python3
"""Driver status management functions for order workflow"""

from app import app, db
from models import Driver, Order

def update_driver_status_on_order_acceptance(driver_id, order_id):
    """Set driver status to BUSY when they accept an order"""
    with app.app_context():
        driver = Driver.query.get(driver_id)
        if driver:
            driver.is_available = False  # BUSY
            db.session.commit()
            print(f"Driver {driver.name} status changed to BUSY (accepting order #{order_id})")
            return True
        return False

def update_driver_status_on_order_completion(driver_id, order_id):
    """Set driver status to AVAILABLE when they complete an order"""
    with app.app_context():
        driver = Driver.query.get(driver_id)
        if driver:
            # Check if driver has any other active orders
            other_active_orders = Order.query.filter(
                Order.driver_id == driver_id,
                Order.id != order_id,
                Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
            ).count()
            
            if other_active_orders == 0:
                driver.is_available = True  # AVAILABLE
                print(f"Driver {driver.name} status changed to AVAILABLE (completed order #{order_id})")
            else:
                print(f"Driver {driver.name} remains BUSY (has {other_active_orders} other active orders)")
            
            db.session.commit()
            return True
        return False

def get_available_drivers_for_restaurant(restaurant_id):
    """Get all available drivers (from any restaurant) for order assignment"""
    with app.app_context():
        available_drivers = Driver.query.filter(
            Driver.is_available == True,
            Driver.approval_status == 'approved',
            Driver.is_active == True
        ).all()
        
        return available_drivers

if __name__ == '__main__':
    # Test the functions
    with app.app_context():
        drivers = Driver.query.all()
        print("Current driver statuses:")
        for driver in drivers:
            status = "AVAILABLE" if driver.is_available else "BUSY"
            restaurant_name = "Flavour cafe" if driver.restaurant_id == 1 else "Rich Cafe"
            print(f"  {driver.name} ({restaurant_name}): {status}")