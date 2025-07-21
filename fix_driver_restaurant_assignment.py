#!/usr/bin/env python3
"""
Fix driver restaurant assignment issue
- Add restaurant_id column to driver table
- Assign approved drivers to Flavour Cafe restaurant
"""

import sqlite3
import sys
from datetime import datetime

def connect_db():
    """Connect to the database"""
    try:
        conn = sqlite3.connect('instance/database.db')
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def add_restaurant_id_column(conn):
    """Add restaurant_id column to driver table"""
    try:
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(driver)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'restaurant_id' not in columns:
            print("Adding restaurant_id column to driver table...")
            cursor.execute("""
                ALTER TABLE driver 
                ADD COLUMN restaurant_id INTEGER 
                REFERENCES restaurant(id)
            """)
            conn.commit()
            print("✅ restaurant_id column added successfully")
        else:
            print("✅ restaurant_id column already exists")
            
    except Exception as e:
        print(f"Error adding restaurant_id column: {e}")
        return False
    
    return True

def get_flavour_cafe_id(conn):
    """Get the restaurant ID for Flavour Cafe"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM restaurant WHERE name LIKE '%Flavour%' OR name LIKE '%E.Fabrica%'")
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            print("❌ Flavour Cafe restaurant not found")
            return None
    except Exception as e:
        print(f"Error getting restaurant ID: {e}")
        return None

def assign_drivers_to_restaurant(conn, restaurant_id):
    """Assign all approved drivers to Flavour Cafe restaurant"""
    try:
        cursor = conn.cursor()
        
        # Get all approved drivers without restaurant assignment
        cursor.execute("""
            SELECT id, name, approval_status, is_approved 
            FROM driver 
            WHERE (restaurant_id IS NULL OR restaurant_id = 0) 
            AND approval_status = 'approved' 
            AND is_approved = 1
        """)
        drivers = cursor.fetchall()
        
        if not drivers:
            print("❌ No approved drivers found to assign")
            return False
        
        print(f"Found {len(drivers)} approved drivers to assign:")
        for driver in drivers:
            print(f"  - {driver[1]} (ID: {driver[0]})")
        
        # Assign all approved drivers to the restaurant
        cursor.execute("""
            UPDATE driver 
            SET restaurant_id = ? 
            WHERE (restaurant_id IS NULL OR restaurant_id = 0) 
            AND approval_status = 'approved' 
            AND is_approved = 1
        """, (restaurant_id,))
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        print(f"✅ Successfully assigned {affected_rows} drivers to Flavour Cafe restaurant")
        return True
        
    except Exception as e:
        print(f"Error assigning drivers to restaurant: {e}")
        return False

def verify_assignment(conn, restaurant_id):
    """Verify the driver assignments"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.id, d.name, d.approval_status, r.name as restaurant_name
            FROM driver d
            LEFT JOIN restaurant r ON d.restaurant_id = r.id
            WHERE d.restaurant_id = ?
        """, (restaurant_id,))
        
        drivers = cursor.fetchall()
        
        if drivers:
            print(f"\n✅ Verification: {len(drivers)} drivers assigned to restaurant:")
            for driver in drivers:
                print(f"  - {driver[1]} → {driver[3]}")
        else:
            print("❌ No drivers found assigned to restaurant")
            
    except Exception as e:
        print(f"Error verifying assignments: {e}")

def main():
    """Main function"""
    print("=" * 60)
    print("🔧 FIXING DRIVER RESTAURANT ASSIGNMENT")
    print("=" * 60)
    
    # Connect to database
    conn = connect_db()
    if not conn:
        sys.exit(1)
    
    try:
        # Step 1: Add restaurant_id column
        if not add_restaurant_id_column(conn):
            sys.exit(1)
        
        # Step 2: Get Flavour Cafe restaurant ID
        restaurant_id = get_flavour_cafe_id(conn)
        if not restaurant_id:
            sys.exit(1)
        
        print(f"✅ Found Flavour Cafe restaurant (ID: {restaurant_id})")
        
        # Step 3: Assign drivers to restaurant
        if not assign_drivers_to_restaurant(conn, restaurant_id):
            sys.exit(1)
        
        # Step 4: Verify assignments
        verify_assignment(conn, restaurant_id)
        
        print("\n🎉 Driver restaurant assignment completed successfully!")
        print("✅ Approved drivers should now appear in Flavour Cafe's driver management section")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()