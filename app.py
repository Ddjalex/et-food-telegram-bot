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
            MenuItem(name="Beef Burger Normal", price=400.0, description="Delicious beef burger with classic toppings", category="burgers", image_url="https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Beef Burger Special", price=460.0, description="Special beef burger with premium ingredients", category="burgers", image_url="https://images.unsplash.com/photo-1594212699903-ec8a3eca50f5?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Chicken Burger Normal", price=485.0, description="Tasty chicken burger with fresh vegetables", category="burgers", image_url="https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Chicken Burger Special", price=540.0, description="Premium chicken burger with special sauce", category="burgers", image_url="/static/uploads/1751965845_Chicken_Burger_Special.jpg"),
            
            # Shawarma Category
            MenuItem(name="Beef Shawarama Large", price=495.0, description="Large beef shawarma with traditional spices", category="shawarma", image_url="/static/uploads/1751974703_Beef_Shawarama_Large.jpg"),
            MenuItem(name="Beef Shawarama Small", price=275.0, description="Small beef shawarma perfect for light meal", category="shawarma", image_url="/static/uploads/1751974754_images_22.jpg"),
            MenuItem(name="Chicken Shawarama Large", price=600.0, description="Large chicken shawarma with fresh vegetables", category="shawarma", image_url="/static/uploads/1751974821_Chicken-Shawarma-7-728x1094.jpg"),
            MenuItem(name="Chicken Shawarama Small", price=430.0, description="Small chicken shawarma with authentic taste", category="shawarma", image_url="/static/uploads/1751977767_images_52.jpg"),
            
            # Sandwiches & Wraps Category
            MenuItem(name="Chicken Wrap", price=385.0, description="Chicken wrap with fresh vegetables", category="sandwiches & wraps", image_url="/static/uploads/1751974872_images_23.jpg"),
            MenuItem(name="Club Sandwich", price=385.0, description="Classic club sandwich with layers of goodness", category="sandwiches & wraps", image_url="/static/uploads/1751974915_images_24.jpg"),
            MenuItem(name="Tunna Sandwich", price=330.0, description="Tuna sandwich with mayo and vegetables", category="sandwiches & wraps", image_url="/static/uploads/1751975047_images_25.jpg"),
            MenuItem(name="Tunna Wrap", price=330.0, description="Tuna wrap with fresh ingredients", category="sandwiches & wraps", image_url="/static/uploads/1751975080_images_26.jpg"),
            MenuItem(name="Vegetable Wrap", price=220.0, description="Healthy vegetable wrap with fresh greens", category="sandwiches & wraps", image_url="/static/uploads/1751975114_images_27.jpg"),
            MenuItem(name="Ahu Wrap", price=300.0, description="Special Ahu wrap with unique flavors", category="sandwiches & wraps", image_url="/static/uploads/1751975388_images_28.jpg"),
            
            # Pizza Category
            MenuItem(name="Chicken Pizza", price=600.0, description="Delicious chicken pizza with cheese and vegetables", category="pizza", image_url="https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Special Pizza", price=650.0, description="Special pizza with premium toppings", category="pizza", image_url="https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Vegetable Pizza", price=400.0, description="Vegetable pizza with fresh garden vegetables", category="pizza", image_url="https://images.unsplash.com/photo-1604382354936-07c5d9983bd3?w=400&h=300&fit=crop&auto=format"),
            
            # Pasta Category
            MenuItem(name="Pasta With Chicken", price=330.0, description="Pasta served with tender chicken pieces", category="pasta", image_url="https://images.unsplash.com/photo-1611270629569-8b357cb88da9?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Pasta With Tomato", price=200.0, description="Classic pasta with tomato sauce", category="pasta", image_url="/static/uploads/1751975454_images_29.jpg"),
            MenuItem(name="Pasta With Tunna", price=295.0, description="Pasta with tuna and herbs", category="pasta", image_url="/static/uploads/1751975519_images_30.jpg"),
            MenuItem(name="Pasta With Vegetable", price=265.0, description="Pasta with mixed vegetables", category="pasta", image_url="https://images.unsplash.com/photo-1555949258-eb67b1ef0ceb?w=400&h=300&fit=crop&auto=format"),
            
            # Borrito Category
            MenuItem(name="Borrito", price=440.0, description="Delicious borrito with meat and vegetables", category="borrito", image_url="https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Borrito Fasting", price=385.0, description="Vegetarian borrito perfect for fasting", category="borrito", image_url="/static/uploads/1751975669_images_31.jpg"),
            
            # Rice Dishes Category
            MenuItem(name="Rice with Chicken", price=385.0, description="Rice served with seasoned chicken", category="rice dishes", image_url="/static/uploads/1751975725_images_32.jpg"),
            MenuItem(name="Rice with Tomato", price=240.0, description="Rice with tomato sauce and herbs", category="rice dishes", image_url="https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Rice with Tunna", price=360.0, description="Rice with tuna and vegetables", category="rice dishes", image_url="https://images.unsplash.com/photo-1512058564366-18510be2db19?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Rice with Vegetable", price=280.0, description="Rice with mixed vegetables", category="rice dishes", image_url="/static/uploads/1751975777_Easy-Mixed-Vegetable-Rice-Sq-Pic.jpg"),
            
            # Egg Dishes & Toast Category
            MenuItem(name="Egg Sandwich", price=175.0, description="Fresh egg sandwich with vegetables", category="egg dishes & toast", image_url="/static/uploads/1751974964_fried-egg-sandwich.webp"),
            MenuItem(name="Egg Crumble", price=165.0, description="Scrambled eggs with spices", category="egg dishes & toast", image_url="/static/uploads/1751975863_images_33.jpg"),
            MenuItem(name="Egg With Avocado", price=180.0, description="Egg served with fresh avocado", category="egg dishes & toast", image_url="/static/uploads/1751976095_Avocado-Egg-Salad-Sandwich-Recipe-Piping-Pot-Curry.webp"),
            MenuItem(name="Omlet", price=200.0, description="Fluffy omelet with herbs", category="egg dishes & toast", image_url="/static/uploads/1751976139_images_34.jpg"),
            MenuItem(name="French Toast", price=180.0, description="Classic French toast with syrup", category="egg dishes & toast", image_url="/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg"),
            
            # Fries & Pancakes Category
            MenuItem(name="French Fries", price=110.0, description="Crispy golden french fries", category="fries & pancakes", image_url="https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Pan Cake", price=240.0, description="Fluffy pancakes with syrup", category="fries & pancakes", image_url="https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=300&fit=crop&auto=format"),
            MenuItem(name="Wafil Kuckis", price=175.0, description="Waffle cookies with sweet topping", category="fries & pancakes", image_url="/static/uploads/1751976469_images_38.jpg"),
            
            # Traditional Ethiopian Breakfast Category
            MenuItem(name="Ahu Special Breakfast", price=330.0, description="Special Ethiopian breakfast combination", category="traditional ethiopian breakfast", image_url="/static/uploads/1751976624_vegan-breakfast.jpg"),
            MenuItem(name="Special Chechebsa", price=240.0, description="Special version of traditional chechebsa", category="traditional ethiopian breakfast", image_url="/static/uploads/1751977000_images_44.jpg"),
            MenuItem(name="Normal Ertib", price=165.0, description="Traditional Ethiopian bread", category="traditional ethiopian breakfast", image_url="/static/uploads/1751976758_images_40.jpg"),
            MenuItem(name="Special Foul", price=200.0, description="Special Ethiopian foul with extras", category="traditional ethiopian breakfast", image_url="/static/uploads/1751977211_foul-at-no-name-cafe.jpg"),
            
            # Extras Category
            MenuItem(name="Extra Cheese", price=40.0, description="Additional cheese topping", category="extras", image_url="/static/uploads/1751977528_images_49.jpg"),
            MenuItem(name="Extra Tunna", price=70.0, description="Additional tuna portion", category="extras", image_url="/static/uploads/1751977663_images_51.jpg"),
            MenuItem(name="Extra Avocado", price=30.0, description="Additional avocado topping", category="extras", image_url="/static/uploads/1751977366_images_46.jpg")
        ]
        for item in default_items:
            db.session.add(item)
        
        # Create default categories
        default_categories = [
            Category(name='Burgers', description='Delicious burgers and sandwiches', icon='🍔', sort_order=1),
            Category(name='Shawarma', description='Middle Eastern wrapped delights', icon='🌯', sort_order=2),
            Category(name='Sandwiches & Wraps', description='Fresh sandwiches and wraps', icon='🥪', sort_order=3),
            Category(name='Pizza', description='Italian style pizzas', icon='🍕', sort_order=4),
            Category(name='Pasta', description='Italian pasta dishes', icon='🍝', sort_order=5),
            Category(name='Borrito', description='Mexican style burritos', icon='🌯', sort_order=6),
            Category(name='Rice Dishes', description='Rice-based meals', icon='🍚', sort_order=7),
            Category(name='Egg Dishes & Toast', description='Breakfast and egg dishes', icon='🥚', sort_order=8),
            Category(name='Fries & Pancakes', description='Fries and pancakes', icon='🍟', sort_order=9),
            Category(name='Traditional Ethiopian Breakfast', description='Ethiopian traditional breakfast', icon='🫓', sort_order=10),
            Category(name='Extras', description='Additional toppings and sides', icon='➕', sort_order=11)
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

