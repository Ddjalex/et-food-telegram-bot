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
        
        # Initialize default data if needed
        from models import Category, MenuItem
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