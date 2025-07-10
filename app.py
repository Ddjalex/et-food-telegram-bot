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
    if not MenuItem.query.first() or not Category.query.first():
        default_items = [
            # Burgers Category
            MenuItem(name="Classic Beef Burger", price=120.00, description="Juicy beef patty with lettuce, tomato, and cheese", category="burgers", image_url="https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400"),
            MenuItem(name="Chicken Burger", price=110.00, description="Crispy chicken breast with special sauce", category="burgers", image_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400"),
            MenuItem(name="Turkey Burger", price=130.00, description="Lean turkey patty with avocado", category="burgers", image_url="https://images.unsplash.com/photo-1546793665-c74683f339c1?w=400"),
            MenuItem(name="Veggie Burger", price=100.00, description="Plant-based patty with fresh vegetables", category="burgers", image_url="https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400"),
            
            # Shawarma Category
            MenuItem(name="Chicken Shawarma", price=90.00, description="Marinated chicken with garlic sauce", category="shawarma", image_url="https://images.unsplash.com/photo-1529006557810-274b9b2fc783?w=400"),
            MenuItem(name="Beef Shawarma", price=110.00, description="Tender beef with tahini sauce", category="shawarma", image_url="https://images.unsplash.com/photo-1529006557810-274b9b2fc783?w=400"),
            MenuItem(name="Mixed Shawarma", price=120.00, description="Combination of chicken and beef", category="shawarma", image_url="https://images.unsplash.com/photo-1529006557810-274b9b2fc783?w=400"),
            
            # Pizza Category
            MenuItem(name="Margherita Pizza", price=180.00, description="Fresh mozzarella, tomato sauce, and basil", category="pizza", image_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400"),
            MenuItem(name="Pepperoni Pizza", price=220.00, description="Classic pepperoni with mozzarella cheese", category="pizza", image_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400"),
            MenuItem(name="Vegetarian Pizza", price=200.00, description="Mixed vegetables with cheese", category="pizza", image_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400"),
            
            # Pasta Category
            MenuItem(name="Spaghetti Bolognese", price=140.00, description="Classic meat sauce with pasta", category="pasta", image_url="https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=400"),
            MenuItem(name="Fettuccine Alfredo", price=130.00, description="Creamy white sauce with fettuccine", category="pasta", image_url="https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=400"),
            MenuItem(name="Penne Arrabbiata", price=120.00, description="Spicy tomato sauce with penne pasta", category="pasta", image_url="https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=400"),
            
            # Drinks Category
            MenuItem(name="Coca Cola", price=25.00, description="Classic refreshing cola", category="drinks", image_url="https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?w=400"),
            MenuItem(name="Orange Juice", price=30.00, description="Fresh orange juice", category="drinks", image_url="https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400"),
            MenuItem(name="Mineral Water", price=20.00, description="Still mineral water", category="drinks", image_url="https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=400"),
            
            # Sides Category
            MenuItem(name="French Fries", price=50.00, description="Crispy golden french fries", category="sides", image_url="https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400"),
            MenuItem(name="Onion Rings", price=60.00, description="Crispy battered onion rings", category="sides", image_url="https://images.unsplash.com/photo-1639024471283-03518883512d?w=400"),
            MenuItem(name="Chicken Wings", price=80.00, description="Spicy chicken wings with sauce", category="sides", image_url="https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400")
        ]
        for item in default_items:
            db.session.add(item)
        
        # Create default categories
        default_categories = [
            Category(name='Burgers', description='Delicious burgers and sandwiches', icon='🍔', sort_order=1),
            Category(name='Shawarma', description='Middle Eastern wrapped delights', icon='🌯', sort_order=2),
            Category(name='Pizza', description='Italian style pizzas', icon='🍕', sort_order=3),
            Category(name='Pasta', description='Italian pasta dishes', icon='🍝', sort_order=4),
            Category(name='Sides', description='Side dishes and appetizers', icon='🍟', sort_order=5),
            Category(name='Drinks', description='Beverages and refreshments', icon='🥤', sort_order=6)
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

    # Init bots (after routes are loaded)
    from bot_minimal import init_bot
    init_bot(app)
    
    # Init driver bot
    try:
        from driver_bot import init_driver_bot
        init_driver_bot(app)
    except Exception as e:
        logging.warning(f"Driver bot initialization failed: {e}")
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

