"""
Migration script to add multi-restaurant support to existing database
"""
import sqlite3
from app import app, db
from models import Restaurant, MenuItem, Order

def migrate_database():
    """Migrate existing database to support multi-restaurant"""
    with app.app_context():
        try:
            # Check if Restaurant table exists
            inspector = db.inspect(db.engine)
            if 'restaurant' not in inspector.get_table_names():
                print("Creating restaurant table...")
                db.create_all()
                print("Restaurant table created successfully!")
            
            # Check if restaurant_id column exists in MenuItem table
            menu_columns = [col['name'] for col in inspector.get_columns('menu_item')]
            if 'restaurant_id' not in menu_columns:
                print("Adding restaurant_id column to MenuItem table...")
                
                # Add restaurant_id column to MenuItem table
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE menu_item ADD COLUMN restaurant_id INTEGER DEFAULT 1'))
                    conn.commit()
                print("restaurant_id column added to MenuItem table!")
            
            # Check if restaurant_id column exists in Order table
            order_columns = [col['name'] for col in inspector.get_columns('order')]
            if 'restaurant_id' not in order_columns:
                print("Adding restaurant_id column to Order table...")
                
                # Add restaurant_id column to Order table
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "order" ADD COLUMN restaurant_id INTEGER DEFAULT 1'))
                    conn.commit()
                print("restaurant_id column added to Order table!")
            
            # Ensure we have at least one restaurant
            if Restaurant.query.count() == 0:
                print("Creating default restaurants...")
                # Create default restaurants
                restaurants = [
                    {
                        'name': 'X Factory',
                        'description': 'Premium food factory with authentic flavors',
                        'address': 'Addis Ababa, Ethiopia',
                        'phone': '+251911123456',
                        'latitude': 9.0579,
                        'longitude': 38.7914,
                        'is_active': True,
                        'is_featured': True,
                        'delivery_fee': 50.0,
                        'minimum_order': 200.0,
                        'estimated_delivery_time': '30-45 minutes',
                        'opening_hours': {
                            'monday': '09:00-22:00',
                            'tuesday': '09:00-22:00',
                            'wednesday': '09:00-22:00',
                            'thursday': '09:00-22:00',
                            'friday': '09:00-22:00',
                            'saturday': '09:00-22:00',
                            'sunday': '09:00-22:00'
                        }
                    },
                    {
                        'name': 'Y Factory Restaurant',
                        'description': 'Modern restaurant with diverse cuisine',
                        'address': 'Addis Ababa, Ethiopia',
                        'phone': '+251911654321',
                        'latitude': 9.0519,
                        'longitude': 38.7269,
                        'is_active': True,
                        'is_featured': False,
                        'delivery_fee': 40.0,
                        'minimum_order': 150.0,
                        'estimated_delivery_time': '25-40 minutes',
                        'opening_hours': {
                            'monday': '08:00-23:00',
                            'tuesday': '08:00-23:00',
                            'wednesday': '08:00-23:00',
                            'thursday': '08:00-23:00',
                            'friday': '08:00-23:00',
                            'saturday': '08:00-23:00',
                            'sunday': '08:00-23:00'
                        }
                    }
                ]
                
                for rest_data in restaurants:
                    restaurant = Restaurant(**rest_data)
                    db.session.add(restaurant)
                
                db.session.commit()
                print("Default restaurants created!")
            
            print("✅ Database migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()

if __name__ == '__main__':
    migrate_database()