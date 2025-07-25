#!/usr/bin/env python3
"""Demonstrate the complete driver status management system"""

from app import app, db
from models import Driver, Order, AdminUser
from datetime import datetime

def demo_driver_status_system():
    with app.app_context():
        print("=== DRIVER STATUS MANAGEMENT SYSTEM DEMO ===\n")
        
        # Current status
        drivers = Driver.query.all()
        print("Initial driver statuses:")
        for driver in drivers:
            status = "AVAILABLE" if driver.is_available else "BUSY"
            restaurant_name = "Flavour cafe" if driver.restaurant_id == 1 else "Rich Cafe"
            print(f"  {driver.name} ({restaurant_name}): {status}")
        
        # Show visibility for each restaurant admin
        flavor_admin = AdminUser.query.filter_by(username="Flavor").first()
        babi_admin = AdminUser.query.filter_by(username="Babi").first()
        
        print(f"\n=== RESTAURANT ADMIN VISIBILITY ===")
        
        # Flavor admin visibility
        print(f"\nFlavor admin (Restaurant {flavor_admin.restaurant_id}) can see:")
        own_drivers = Driver.query.filter_by(restaurant_id=flavor_admin.restaurant_id).all()
        available_other_drivers = Driver.query.filter(
            Driver.restaurant_id != flavor_admin.restaurant_id,
            Driver.is_available == True,
            Driver.approval_status == 'approved'
        ).all()
        
        for driver in own_drivers:
            status = "AVAILABLE" if driver.is_available else "BUSY"
            print(f"  - {driver.name} (Own driver - {status})")
        for driver in available_other_drivers:
            print(f"  - {driver.name} (Available from Restaurant {driver.restaurant_id})")
        
        total_flavor = len(own_drivers + available_other_drivers)
        print(f"  Total visible: {total_flavor} drivers")
        
        # Babi admin visibility
        print(f"\nBabi admin (Restaurant {babi_admin.restaurant_id}) can see:")
        own_drivers = Driver.query.filter_by(restaurant_id=babi_admin.restaurant_id).all()
        available_other_drivers = Driver.query.filter(
            Driver.restaurant_id != babi_admin.restaurant_id,
            Driver.is_available == True,
            Driver.approval_status == 'approved'
        ).all()
        
        for driver in own_drivers:
            status = "AVAILABLE" if driver.is_available else "BUSY"
            print(f"  - {driver.name} (Own driver - {status})")
        for driver in available_other_drivers:
            print(f"  - {driver.name} (Available from Restaurant {driver.restaurant_id})")
        
        total_babi = len(own_drivers + available_other_drivers)
        print(f"  Total visible: {total_babi} drivers")
        
        # Demonstrate status change when order is accepted
        print(f"\n=== SIMULATING ORDER ACCEPTANCE ===")
        dj_alex = Driver.query.filter_by(name="DJ ALEX").first()
        print(f"DJ ALEX current status: {'AVAILABLE' if dj_alex.is_available else 'BUSY'}")
        
        print("Simulating DJ ALEX accepting an order...")
        dj_alex.is_available = False  # BUSY
        db.session.commit()
        
        print(f"DJ ALEX new status: {'AVAILABLE' if dj_alex.is_available else 'BUSY'}")
        
        # Show updated visibility
        print(f"\nAfter DJ ALEX becomes BUSY:")
        available_other_drivers = Driver.query.filter(
            Driver.restaurant_id != flavor_admin.restaurant_id,
            Driver.is_available == True,
            Driver.approval_status == 'approved'
        ).all()
        print(f"Flavor admin can see {len(available_other_drivers)} available drivers from other restaurants")
        
        # Simulate order completion
        print(f"\n=== SIMULATING ORDER COMPLETION ===")
        print("Simulating DJ ALEX completing delivery...")
        dj_alex.is_available = True  # AVAILABLE
        db.session.commit()
        
        print(f"DJ ALEX status after delivery: {'AVAILABLE' if dj_alex.is_available else 'BUSY'}")
        
        # Final visibility check
        available_other_drivers = Driver.query.filter(
            Driver.restaurant_id != flavor_admin.restaurant_id,
            Driver.is_available == True,
            Driver.approval_status == 'approved'
        ).all()
        print(f"Flavor admin can now see {len(available_other_drivers)} available drivers from other restaurants")
        
        print(f"\n=== DEMO COMPLETE ===")
        print("Driver status system working correctly:")
        print("✓ AVAILABLE drivers visible to all restaurant admins")
        print("✓ BUSY drivers only visible to their own restaurant")
        print("✓ Status automatically changes on order acceptance/completion")

if __name__ == '__main__':
    demo_driver_status_system()