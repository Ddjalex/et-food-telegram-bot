"""
Flask Application Configuration for MongoDB
ET-FOOD Delivery System
"""
import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# MongoDB connection string
MONGO_URI = "mongodb+srv://almeseged:A1l2m3e4s5@cluster0.t6sz6bo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create the app with explicit static configuration
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get("SESSION_SECRET", "et-food-secret-key-2025-mongo-migration")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure MongoDB connection (direct connection managed in models)
app.config["MONGO_URI"] = MONGO_URI

# Import models to ensure collections are available
import models_mongo

def init_mongodb():
    """Initialize MongoDB with default data"""
    from models_mongo import restaurant_model, category_model, menu_item_model, admin_user_model
    
    # Create default restaurants if none exist
    if restaurant_model.count() == 0:
        print("Creating default restaurants...")
        
        # Create Flavour cafe restaurant
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
        
        # Create Y Factory restaurant
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
        
        print(f"Created restaurants: {flavour_id}, {y_factory_id}")
    
    # Create default categories if none exist
    if category_model.count() == 0:
        print("Creating default categories...")
        categories = [
            {"name": "Burgers", "description": "Delicious beef and chicken burgers", "icon": "🍔", "sort_order": 1},
            {"name": "Shawarma", "description": "Traditional Middle Eastern wraps", "icon": "🌯", "sort_order": 2},
            {"name": "Sandwiches & Wraps", "description": "Fresh sandwiches and wraps", "icon": "🥪", "sort_order": 3},
            {"name": "Pizza", "description": "Italian style pizzas", "icon": "🍕", "sort_order": 4},
            {"name": "Pasta", "description": "Italian pasta dishes", "icon": "🍝", "sort_order": 5},
            {"name": "Burrito", "description": "Mexican burritos", "icon": "🌯", "sort_order": 6},
            {"name": "Rice Dishes", "description": "Variety of rice based meals", "icon": "🍚", "sort_order": 7},
            {"name": "Egg Dishes & Toast", "description": "Breakfast and egg dishes", "icon": "🍳", "sort_order": 8},
            {"name": "Fries & Pancakes", "description": "Sides and pancakes", "icon": "🥞", "sort_order": 9},
            {"name": "Traditional Ethiopian Breakfast", "description": "Authentic Ethiopian breakfast", "icon": "☕", "sort_order": 10},
            {"name": "Extras", "description": "Additional items and sides", "icon": "🥗", "sort_order": 11},
            {"name": "Drinks", "description": "Beverages and drinks", "icon": "🥤", "sort_order": 12},
            {"name": "Snacks", "description": "Light snacks and appetizers", "icon": "🍿", "sort_order": 13},
            {"name": "Sauces", "description": "Various sauces and condiments", "icon": "🥄", "sort_order": 14}
        ]
        
        for cat_data in categories:
            category_model.create(**cat_data)
        
        print(f"Created {len(categories)} categories")
    
    # Create default menu items if none exist
    if menu_item_model.count() == 0:
        print("Creating default menu items...")
        
        # Get first restaurant for menu items
        restaurants = restaurant_model.find_many()
        if restaurants:
            restaurant_id = restaurants[0]['id']
            
            menu_items = [
                # BURGERS CATEGORY
                {"name": "Beef Burger Normal", "price": 400.0, "description": "Delicious beef burger with classic toppings", "category": "Burgers", "image_url": "/static/uploads/beef_burger_normal.jpg"},
                {"name": "Chicken Burger Special", "price": 540.0, "description": "Premium chicken burger with special sauce", "category": "Burgers", "image_url": "/static/uploads/chicken_burger_special.jpg"},
                {"name": "Cheese Burger", "price": 450.0, "description": "Juicy burger with melted cheese", "category": "Burgers", "image_url": "/static/uploads/cheese_burger.jpg"},
                
                # SHAWARMA CATEGORY
                {"name": "Beef Shawarma Large", "price": 495.0, "description": "Large beef shawarma with traditional spices", "category": "Shawarma", "image_url": "/static/uploads/beef_shawarma_large.jpg"},
                {"name": "Chicken Shawarma Small", "price": 430.0, "description": "Small chicken shawarma with authentic taste", "category": "Shawarma", "image_url": "/static/uploads/chicken_shawarma_small.jpg"},
                
                # TRADITIONAL ETHIOPIAN
                {"name": "Injera with Doro Wat", "price": 350.0, "description": "Traditional Ethiopian injera with spicy chicken stew", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/injera_doro_wat.jpg"},
                {"name": "Kitfo", "price": 280.0, "description": "Ethiopian beef tartare", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/kitfo.jpg"},
                {"name": "Tibs", "price": 320.0, "description": "Ethiopian sautéed meat", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/tibs.jpg"},
                {"name": "Shiro Wat", "price": 180.0, "description": "Ethiopian chickpea stew", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/shiro_wat.jpg"},
                
                # PIZZA CATEGORY
                {"name": "Margherita Pizza", "price": 450.0, "description": "Classic pizza with tomato and mozzarella", "category": "Pizza", "image_url": "/static/uploads/margherita_pizza.jpg"},
                {"name": "Pepperoni Pizza", "price": 520.0, "description": "Pizza with pepperoni and cheese", "category": "Pizza", "image_url": "/static/uploads/pepperoni_pizza.jpg"},
                
                # PASTA CATEGORY
                {"name": "Spaghetti Bolognese", "price": 380.0, "description": "Classic spaghetti with meat sauce", "category": "Pasta", "image_url": "/static/uploads/spaghetti_bolognese.jpg"},
                {"name": "Fettuccine Alfredo", "price": 420.0, "description": "Creamy fettuccine with alfredo sauce", "category": "Pasta", "image_url": "/static/uploads/fettuccine_alfredo.jpg"},
                
                # RICE DISHES
                {"name": "Chicken Fried Rice", "price": 280.0, "description": "Fried rice with chicken and vegetables", "category": "Rice Dishes", "image_url": "/static/uploads/chicken_fried_rice.jpg"},
                {"name": "Beef Fried Rice", "price": 320.0, "description": "Fried rice with beef and spices", "category": "Rice Dishes", "image_url": "/static/uploads/beef_fried_rice.jpg"},
                
                # EGG DISHES
                {"name": "Scrambled Eggs on Toast", "price": 150.0, "description": "Fluffy scrambled eggs on toast", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/scrambled_eggs.jpg"},
                {"name": "Avocado Toast", "price": 250.0, "description": "Toast with fresh avocado", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/avocado_toast.jpg"},
                
                # FRIES & PANCAKES
                {"name": "Classic French Fries", "price": 120.0, "description": "Crispy golden french fries", "category": "Fries & Pancakes", "image_url": "/static/uploads/french_fries.jpg"},
                {"name": "Sweet Potato Fries", "price": 150.0, "description": "Healthy sweet potato fries", "category": "Fries & Pancakes", "image_url": "/static/uploads/sweet_potato_fries.jpg"},
                {"name": "Fluffy Pancakes", "price": 180.0, "description": "Fluffy pancakes with syrup", "category": "Fries & Pancakes", "image_url": "/static/uploads/pancakes.jpg"},
                
                # DRINKS
                {"name": "Ethiopian Coffee", "price": 80.0, "description": "Traditional Ethiopian coffee", "category": "Drinks", "image_url": "/static/uploads/coffee.jpg"},
                {"name": "Fresh Juice", "price": 120.0, "description": "Freshly squeezed fruit juice", "category": "Drinks", "image_url": "/static/uploads/juice.jpg"},
                {"name": "Soft Drink", "price": 60.0, "description": "Carbonated soft drink", "category": "Drinks", "image_url": "/static/uploads/soft_drink.jpg"}
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
        
        # Create super admin
        admin_user_model.create(
            username='admin',
            password_hash='admin123',  # In production, this should be properly hashed
            role='super_admin'
        )
        
        admin_user_model.create(
            username='superadmin',
            password_hash='superadmin123',  # In production, this should be properly hashed
            role='super_admin'
        )
        
        print("Created admin users")

# Initialize MongoDB collections on startup
with app.app_context():
    init_mongodb()

# Import routes after app configuration
import routes_mongo  # noqa: F401
import admin_routes_mongo  # noqa: F401

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)