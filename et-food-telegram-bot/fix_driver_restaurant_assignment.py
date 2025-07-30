#!/usr/bin/env python3
"""Fix driver restaurant assignment and verify correct filtering"""

from app import app, db
from models import Driver, AdminUser, Restaurant

def fix_driver_restaurant_assignment():
    with app.app_context():
        # Get restaurants
        flavour_cafe = Restaurant.query.filter_by(name="Flavour cafe | E.Fabrica").first()
        rich_cafe = Restaurant.query.filter_by(name="Rich Cafe").first()
        
        print(f"Flavour Cafe ID: {flavour_cafe.id if flavour_cafe else 'Not found'}")
        print(f"Rich Cafe ID: {rich_cafe.id if rich_cafe else 'Not found'}")
        
        # Get admins
        flavor_admin = AdminUser.query.filter_by(username="Flavor").first()
        babi_admin = AdminUser.query.filter_by(username="Babi").first()
        
        print(f"Flavor admin restaurant_id: {flavor_admin.restaurant_id if flavor_admin else 'Not found'}")
        print(f"Babi admin restaurant_id: {babi_admin.restaurant_id if babi_admin else 'Not found'}")
        
        # Get all drivers
        drivers = Driver.query.all()
        print(f"\nCurrent driver assignments:")
        for driver in drivers:
            print(f"  {driver.name} (ID: {driver.id}) -> Restaurant ID: {driver.restaurant_id}")
        
        # Verify Mike Johnson is assigned to Flavour cafe
        mike = Driver.query.filter_by(name="Mike Johnson").first()
        if mike:
            print(f"\nMike Johnson assignment: Restaurant ID {mike.restaurant_id}")
            if mike.restaurant_id != flavour_cafe.id:
                print(f"ERROR: Mike should be assigned to Flavour cafe (ID: {flavour_cafe.id})")
                mike.restaurant_id = flavour_cafe.id
                print(f"Fixed: Mike Johnson now assigned to restaurant {flavour_cafe.id}")
        
        # Verify DJ ALEX is assigned to Rich Cafe
        dj_alex = Driver.query.filter_by(name="DJ ALEX").first()
        if dj_alex:
            print(f"DJ ALEX assignment: Restaurant ID {dj_alex.restaurant_id}")
            if dj_alex.restaurant_id != rich_cafe.id:
                print(f"ERROR: DJ ALEX should be assigned to Rich Cafe (ID: {rich_cafe.id})")
                dj_alex.restaurant_id = rich_cafe.id
                print(f"Fixed: DJ ALEX now assigned to restaurant {rich_cafe.id}")
        
        try:
            db.session.commit()
            print("\nDriver assignments verified and fixed!")
            
            # Final verification
            print("\nFinal driver-restaurant assignments:")
            for restaurant in [flavour_cafe, rich_cafe]:
                if restaurant:
                    restaurant_drivers = Driver.query.filter_by(restaurant_id=restaurant.id).all()
                    print(f"  {restaurant.name} (ID: {restaurant.id}): {len(restaurant_drivers)} drivers")
                    for driver in restaurant_drivers:
                        print(f"    - {driver.name} (ID: {driver.id})")
                        
        except Exception as e:
            db.session.rollback()
            print(f"Error fixing assignments: {e}")

if __name__ == '__main__':
    fix_driver_restaurant_assignment()