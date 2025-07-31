"""
Flask Application with MongoDB Integration
ET-FOOD Delivery System - Direct PyMongo Implementation
"""
import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the app with explicit static configuration
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get("SESSION_SECRET", "et-food-secret-key-2025-mongo-migration")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# MongoDB connection string - configured as environment variable
MONGO_URI = "mongodb+srv://almeseged:A1l2m3e4s5@cluster0.t6sz6bo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
app.config["MONGO_URI"] = MONGO_URI

def init_mongodb():
    """Initialize MongoDB with default data"""
    try:
        from models_mongo_fixed import (
            restaurant_model, category_model, menu_item_model, admin_user_model
        )
        
        # Create default restaurants if none exist
        if restaurant_model.count() == 0:
            print("Creating default restaurants...")
            
            flavour_id = restaurant_model.create(
                name='Flavour cafe | E.Fabrica',
                description='Authentic Ethiopian and International Cuisine',
                address='Addis Ababa, Ethiopia',
                phone='+251911123456',
                latitude=9.0579,
                longitude=38.7614,
                estimated_delivery_time='30-45 minutes',
                is_active=True,
                is_featured=True
            )
            
            y_factory_id = restaurant_model.create(
                name='Y Factory Restaurant',
                description='Modern restaurant with diverse cuisine',
                address='Addis Ababa, Ethiopia',
                phone='+251922334455',
                latitude=9.0458,
                longitude=38.7575,
                estimated_delivery_time='25-40 minutes',
                is_active=True
            )
            
            print(f"Created restaurants: {flavour_id[:8]}... and {y_factory_id[:8]}...")
        
        # Create default categories if none exist
        if category_model.count() == 0:
            print("Creating default categories...")
            categories = [
                {"name": "Burgers", "description": "Delicious beef and chicken burgers", "icon": "🍔", "sort_order": 1},
                {"name": "Shawarma", "description": "Traditional Middle Eastern wraps", "icon": "🌯", "sort_order": 2},
                {"name": "Pizza", "description": "Italian style pizzas", "icon": "🍕", "sort_order": 3},
                {"name": "Traditional Ethiopian Breakfast", "description": "Authentic Ethiopian breakfast", "icon": "☕", "sort_order": 4},
                {"name": "Drinks", "description": "Beverages and drinks", "icon": "🥤", "sort_order": 5}
            ]
            
            for cat_data in categories:
                category_model.create(**cat_data)
            
            print(f"Created {len(categories)} categories")
        
        # Create default menu items if none exist
        if menu_item_model.count() == 0:
            print("Creating default menu items...")
            
            restaurants = restaurant_model.find_many()
            if restaurants:
                restaurant_id = restaurants[0]['id']
                
                menu_items = [
                    {"name": "Beef Burger Normal", "price": 400.0, "description": "Delicious beef burger with classic toppings", "category": "Burgers", "image_url": "/static/uploads/1751975047_images_25.jpg"},
                    {"name": "Chicken Burger Special", "price": 540.0, "description": "Premium chicken burger with special sauce", "category": "Burgers", "image_url": "/static/uploads/1751975080_images_26.jpg"},
                    {"name": "Beef Shawarma Large", "price": 495.0, "description": "Large beef shawarma with traditional spices", "category": "Shawarma", "image_url": "/static/uploads/1751975388_images_28.jpg"},
                    {"name": "Chicken Shawarma Small", "price": 430.0, "description": "Small chicken shawarma with authentic taste", "category": "Shawarma", "image_url": "/static/uploads/1751975863_images_33.jpg"},
                    {"name": "Injera with Doro Wat", "price": 350.0, "description": "Traditional Ethiopian injera with spicy chicken stew", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/1751975047_images_25.jpg"},
                    {"name": "Kitfo", "price": 280.0, "description": "Ethiopian beef tartare", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/1751975080_images_26.jpg"},
                    {"name": "Margherita Pizza", "price": 450.0, "description": "Classic pizza with tomato and mozzarella", "category": "Pizza", "image_url": "/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg"},
                    {"name": "Ethiopian Coffee", "price": 80.0, "description": "Traditional Ethiopian coffee", "category": "Drinks", "image_url": "/static/uploads/1751975047_images_25.jpg"},
                    {"name": "Fresh Juice", "price": 120.0, "description": "Freshly squeezed fruit juice", "category": "Drinks", "image_url": "/static/uploads/1751975080_images_26.jpg"}
                ]
                
                for item_data in menu_items:
                    menu_item_model.create(
                        name=item_data["name"],
                        price=item_data["price"],
                        restaurant_id=restaurant_id,
                        description=item_data["description"],
                        category=item_data["category"],
                        image_url=item_data["image_url"]
                    )
                
                print(f"Created {len(menu_items)} menu items")
        
        # Create default admin users if none exist
        if admin_user_model.count() == 0:
            print("Creating default admin users...")
            
            admin_user_model.create(
                username='admin',
                password_hash='admin123',
                role='super_admin'
            )
            
            admin_user_model.create(
                username='superadmin',
                password_hash='superadmin123',
                role='super_admin'
            )
            
            print("Created admin users: admin, superadmin")
        
        print("MongoDB initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"Failed to initialize MongoDB data: {e}")
        import traceback
        traceback.print_exc()
        return False

# Initialize MongoDB collections on startup
with app.app_context():
    init_mongodb()

# Import routes after app configuration
import routes_mongo_fixed  # noqa: F401
import admin_routes_mongo_fixed  # noqa: F401

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)