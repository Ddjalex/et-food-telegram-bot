#!/usr/bin/env python3
"""Update driver status system to handle order acceptance and availability"""

from app import app, db
from models import Driver, Order

def update_driver_status_system():
    with app.app_context():
        # Set all drivers to available initially (not accepting orders)
        drivers = Driver.query.all()
        
        print(f"Updating status for {len(drivers)} drivers:")
        
        for driver in drivers:
            # Check if driver has any active orders (not delivered or cancelled)
            active_orders = Order.query.filter(
                Order.driver_id == driver.id,
                Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
            ).count()
            
            if active_orders > 0:
                # Driver is busy with active orders
                driver.is_available = False
                status = "BUSY (has active orders)"
            else:
                # Driver is available for new orders
                driver.is_available = True
                status = "AVAILABLE"
            
            print(f"  {driver.name} (Restaurant {driver.restaurant_id}): {status}")
        
        try:
            db.session.commit()
            print("\nDriver status system updated successfully!")
            
            # Show final status
            print("\nFinal driver availability:")
            for driver in drivers:
                restaurant_name = "Flavour cafe" if driver.restaurant_id == 1 else "Rich Cafe"
                status = "AVAILABLE" if driver.is_available else "BUSY"
                print(f"  {driver.name} ({restaurant_name}): {status}")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error updating driver status: {e}")

if __name__ == '__main__':
    update_driver_status_system()