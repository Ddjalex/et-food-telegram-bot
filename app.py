import os
import logging
from flask import Flask
from extensions import db
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///food_delivery.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

def create_tables():
    """Create database tables and initialize default data"""
    with app.app_context():
        # Import models to ensure tables are created
        import models  # noqa: F401
        db.create_all()
        
        # Initialize default restaurants first
        from models import Restaurant, Category, MenuItem
        if Restaurant.query.count() == 0:
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
            print("Default restaurants created")
        
        # Initialize default categories if needed
        if Category.query.count() == 0:
            # Create default categories
            categories = [
                {'name': 'Burgers', 'description': 'Delicious burgers and sandwiches', 'icon': '🍔'},
                {'name': 'Snacks', 'description': 'Light snacks and appetizers', 'icon': '🍟'},
                {'name': 'Sauces', 'description': 'Various sauces and dips', 'icon': '🥫'},
                {'name': 'Drinks', 'description': 'Beverages and drinks', 'icon': '🥤'},
            ]
            
            for cat_data in categories:
                category = Category(
                    name=cat_data['name'],
                    description=cat_data['description'],
                    icon=cat_data['icon']
                )
                db.session.add(category)
            
            db.session.commit()
            print("Default categories created")

# Create tables
create_tables()

# Import routes to register them
from routes import *  # noqa: F401
from restaurant_routes import *  # noqa: F401

# Initialize bot with webhook
try:
    from bot_minimal import init_bot
    init_bot(app)
    print("Bot initialized successfully")
except Exception as e:
    print(f"Error initializing bot: {e}")
    
# Initialize driver bot if available
try:
    from driver_bot import init_driver_bot
    init_driver_bot(app)
    print("Driver bot initialized successfully")
except Exception as e:
    print(f"Error initializing driver bot: {e}")