import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///food_delivery.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Delay route and model imports until after db/app init
with app.app_context():
    from models import MenuItem, Category, Driver
    db.create_all()

    # Create default menu items if none exist
    if not MenuItem.query.first():
        default_items = [
            # Burgers Category
            MenuItem(name="Turkish Durum burger", price=2.67, description="Traditional Turkish style burger with special spices", category="burgers", image_url="https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400"),
            MenuItem(name="Uzbekistan Burger", price=4.58, description="Local style burger with traditional ingredients", category="burgers", image_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400"),
            MenuItem(name="Junior chicken burger", price=1.25, description="Perfect size chicken burger for kids", category="burgers", image_url="https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400"),
            MenuItem(name="New York burger", price=2.33, description="Classic American style burger", category="burgers", image_url="https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400"),
            
            # Snacks Category  
            MenuItem(name="French Fries", price=1.50, description="Crispy golden french fries", category="snacks", image_url="https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400"),
            MenuItem(name="Chicken Wings", price=3.25, description="Spicy chicken wings with sauce", category="snacks", image_url="https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400"),
            
            # Sauces Category
            MenuItem(name="Garlic Sauce", price=0.50, description="Creamy garlic sauce", category="sauces", image_url="https://images.unsplash.com/photo-1472476443507-c7a5948772fc?w=400"),
            MenuItem(name="BBQ Sauce", price=0.50, description="Smoky BBQ sauce", category="sauces", image_url="https://images.unsplash.com/photo-1472476443507-c7a5948772fc?w=400"),
            
            # Drinks Category
            MenuItem(name="Coca Cola", price=1.00, description="Classic refreshing cola", category="drinks", image_url="https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?w=400"),
            MenuItem(name="Orange Juice", price=1.25, description="Fresh orange juice", category="drinks", image_url="https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400")
        ]
        for item in default_items:
            db.session.add(item)
        
        # Create default categories
        default_categories = [
            Category(name='Burgers', description='Delicious burgers and sandwiches', icon='🍔', sort_order=1),
            Category(name='Snacks', description='Quick bites and appetizers', icon='🍟', sort_order=2),
            Category(name='Sauces', description='Dips and sauces', icon='🥄', sort_order=3),
            Category(name='Drinks', description='Beverages and refreshments', icon='🥤', sort_order=4)
        ]
        for category in default_categories:
            db.session.add(category)
        
        # Create sample driver
        sample_driver = Driver(
            name='Sample Driver',
            phone_number='+251911234567',
            vehicle_type='motorcycle',
            is_active=True,
            is_available=True
        )
        db.session.add(sample_driver)
        
        db.session.commit()

    # Now safe to import routes
    from routes import *

    # Init bot (after routes are loaded)
    from bot_minimal import init_bot
    init_bot(app)
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

