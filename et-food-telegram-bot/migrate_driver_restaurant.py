#!/usr/bin/env python3
"""
Migrate driver table to include restaurant_id and assign approved drivers to Flavour Cafe
"""

from app import app, db
from models import Driver, Restaurant, AdminUser
from sqlalchemy import text

def migrate_database():
    """Add restaurant_id column and assign drivers"""
    print("=" * 60)
    print("🔧 MIGRATING DRIVER RESTAURANT ASSIGNMENT")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Check if column exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('driver')]
            
            if 'restaurant_id' not in columns:
                print("Adding restaurant_id column to driver table...")
                
                # Add the column using raw SQL
                if db.engine.url.drivername == 'postgresql':
                    # PostgreSQL syntax
                    db.session.execute(text("""
                        ALTER TABLE driver 
                        ADD COLUMN restaurant_id INTEGER 
                        REFERENCES restaurant(id)
                    """))
                else:
                    # SQLite syntax
                    db.session.execute(text("""
                        ALTER TABLE driver 
                        ADD COLUMN restaurant_id INTEGER 
                        REFERENCES restaurant(id)
                    """))
                
                db.session.commit()
                print("✅ restaurant_id column added successfully")
            else:
                print("✅ restaurant_id column already exists")
            
            # Get Flavour Cafe restaurant
            flavour_cafe = Restaurant.query.filter(
                (Restaurant.name.like('%Flavour%')) | 
                (Restaurant.name.like('%E.Fabrica%'))
            ).first()
            
            if not flavour_cafe:
                print("❌ Flavour Cafe restaurant not found")
                return False
            
            print(f"✅ Found restaurant: {flavour_cafe.name} (ID: {flavour_cafe.id})")
            
            # Get all approved drivers without restaurant assignment
            unassigned_drivers = Driver.query.filter(
                (Driver.restaurant_id == None) | (Driver.restaurant_id == 0),
                Driver.approval_status == 'approved',
                Driver.is_approved == True
            ).all()
            
            if not unassigned_drivers:
                print("❌ No approved unassigned drivers found")
                
                # Check if there are any drivers at all
                all_drivers = Driver.query.all()
                print(f"📊 Total drivers in database: {len(all_drivers)}")
                
                for driver in all_drivers:
                    print(f"  - {driver.name} (Status: {driver.approval_status}, Approved: {driver.is_approved}, Restaurant: {driver.restaurant_id if hasattr(driver, 'restaurant_id') else 'N/A'})")
                
                return False
            
            print(f"Found {len(unassigned_drivers)} approved drivers to assign:")
            for driver in unassigned_drivers:
                print(f"  - {driver.name} (ID: {driver.id})")
            
            # Assign all approved drivers to Flavour Cafe
            assigned_count = 0
            for driver in unassigned_drivers:
                driver.restaurant_id = flavour_cafe.id
                assigned_count += 1
                print(f"  ✅ Assigned {driver.name} to {flavour_cafe.name}")
            
            db.session.commit()
            print(f"✅ Successfully assigned {assigned_count} drivers to {flavour_cafe.name}")
            
            # Verify assignments
            assigned_drivers = Driver.query.filter_by(restaurant_id=flavour_cafe.id).all()
            print(f"\n✅ Verification: {len(assigned_drivers)} drivers now assigned to {flavour_cafe.name}:")
            for driver in assigned_drivers:
                print(f"  - {driver.name} ({driver.approval_status})")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration error: {e}")
            db.session.rollback()
            return False

def update_driver_api_endpoint():
    """Update the driver API to filter by restaurant"""
    print("\n🔧 Next step: Update driver API to filter by restaurant")
    print("The /api/drivers endpoint needs to be updated to show only restaurant-specific drivers")

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Migration completed successfully!")
        print("✅ Approved drivers should now appear in Flavour Cafe's driver management section")
        update_driver_api_endpoint()
    else:
        print("\n❌ Migration failed")