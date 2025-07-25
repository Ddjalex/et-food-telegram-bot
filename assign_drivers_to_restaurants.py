#!/usr/bin/env python3
"""Assign existing drivers to restaurants for testing"""

from app import app, db
from models import Driver, AdminUser, Restaurant

def assign_drivers_to_restaurants():
    with app.app_context():
        # Get all restaurants
        restaurants = Restaurant.query.all()
        print(f"Found {len(restaurants)} restaurants:")
        for restaurant in restaurants:
            print(f"  - ID: {restaurant.id}, Name: {restaurant.name}")
        
        # Get all drivers
        drivers = Driver.query.all()
        print(f"\nFound {len(drivers)} drivers:")
        for driver in drivers:
            print(f"  - ID: {driver.id}, Name: {driver.name}, Restaurant ID: {driver.restaurant_id}")
        
        if not restaurants:
            print("No restaurants found. Please create restaurants first.")
            return
            
        if not drivers:
            print("No drivers found. Please create drivers first.")
            return
        
        # Assign drivers to restaurants in round-robin fashion
        restaurant_count = len(restaurants)
        for i, driver in enumerate(drivers):
            if driver.restaurant_id is None:
                # Assign to restaurant based on round-robin
                restaurant_index = i % restaurant_count
                driver.restaurant_id = restaurants[restaurant_index].id
                print(f"Assigned driver {driver.name} to restaurant {restaurants[restaurant_index].name}")
        
        try:
            db.session.commit()
            print("\nDriver assignments completed successfully!")
            
            # Show final assignments
            print("\nFinal driver-restaurant assignments:")
            for restaurant in restaurants:
                restaurant_drivers = Driver.query.filter_by(restaurant_id=restaurant.id).all()
                print(f"  {restaurant.name}: {len(restaurant_drivers)} drivers")
                for driver in restaurant_drivers:
                    print(f"    - {driver.name} ({driver.phone_number})")
                    
        except Exception as e:
            db.session.rollback()
            print(f"Error assigning drivers: {e}")

if __name__ == '__main__':
    assign_drivers_to_restaurants()