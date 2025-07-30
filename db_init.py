"""
Database initialization script for ET-FOOD
Handles both SQLite (development) and PostgreSQL (production) environments
"""
import os
from app import app, db
from models import MenuItem, Category, Driver, UserProfile, Order

def initialize_database():
    """Initialize database with tables and default data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully")
        
        # Check if database is empty and populate with default data
        if not Category.query.first():
            create_default_categories()
            
        if not MenuItem.query.first():
            create_default_menu_items()
            
        print("Database initialization completed")

def create_default_categories():
    """Create default food categories"""
    categories = [
        {"name": "Burgers", "description": "Delicious beef and chicken burgers", "icon": "🍔", "sort_order": 1},
        {"name": "Shawarma", "description": "Traditional Middle Eastern wraps", "icon": "🌯", "sort_order": 2},
        {"name": "Sandwiches & Wraps", "description": "Fresh sandwiches and wraps", "icon": "🥪", "sort_order": 3},
        {"name": "Pizza", "description": "Italian style pizzas", "icon": "🍕", "sort_order": 4},
        {"name": "Pasta", "description": "Italian pasta dishes", "icon": "🍝", "sort_order": 5},
        {"name": "Borrito", "description": "Mexican burritos", "icon": "🌯", "sort_order": 6},
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
        category = Category(**cat_data)
        db.session.add(category)
    
    db.session.commit()
    print(f"Created {len(categories)} default categories")

def create_default_menu_items():
    """Create complete ET-FOOD menu with all 64 items"""
    complete_menu = [
        # BURGERS CATEGORY (6 items)
        {"name": "Beef Burger Normal", "price": 400.0, "description": "Delicious beef burger with classic toppings", "category": "Burgers", "image_url": "/static/uploads/beef_burger_normal.jpg"},
        {"name": "Chicken Burger Special", "price": 540.0, "description": "Premium chicken burger with special sauce", "category": "Burgers", "image_url": "/static/uploads/chicken_burger_special.jpg"},
        {"name": "Cheese Burger", "price": 450.0, "description": "Juicy burger with melted cheese", "category": "Burgers", "image_url": "/static/uploads/cheese_burger.jpg"},
        {"name": "BBQ Burger", "price": 480.0, "description": "Smoky BBQ flavored burger", "category": "Burgers", "image_url": "/static/uploads/bbq_burger.jpg"},
        {"name": "Veggie Burger", "price": 350.0, "description": "Healthy vegetarian burger option", "category": "Burgers", "image_url": "/static/uploads/veggie_burger.jpg"},
        {"name": "Double Beef Burger", "price": 650.0, "description": "Double patty beef burger for big appetite", "category": "Burgers", "image_url": "/static/uploads/double_beef_burger.jpg"},
        
        # SHAWARMA CATEGORY (6 items)
        {"name": "Beef Shawarma Large", "price": 495.0, "description": "Large beef shawarma with traditional spices", "category": "Shawarma", "image_url": "/static/uploads/beef_shawarma_large.jpg"},
        {"name": "Chicken Shawarma Small", "price": 430.0, "description": "Small chicken shawarma with authentic taste", "category": "Shawarma", "image_url": "/static/uploads/chicken_shawarma_small.jpg"},
        {"name": "Chicken Shawarma Large", "price": 520.0, "description": "Large chicken shawarma with extra filling", "category": "Shawarma", "image_url": "/static/uploads/chicken_shawarma_large.jpg"},
        {"name": "Beef Shawarma Small", "price": 380.0, "description": "Small beef shawarma perfect for snack", "category": "Shawarma", "image_url": "/static/uploads/beef_shawarma_small.jpg"},
        {"name": "Mixed Shawarma", "price": 560.0, "description": "Combination of beef and chicken shawarma", "category": "Shawarma", "image_url": "/static/uploads/mixed_shawarma.jpg"},
        {"name": "Spicy Shawarma", "price": 480.0, "description": "Extra spicy shawarma with hot sauce", "category": "Shawarma", "image_url": "/static/uploads/spicy_shawarma.jpg"},
        
        # SANDWICHES & WRAPS CATEGORY (5 items)
        {"name": "Club Sandwich", "price": 320.0, "description": "Classic three-layer club sandwich", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/club_sandwich.jpg"},
        {"name": "Chicken Wrap", "price": 280.0, "description": "Grilled chicken wrap with vegetables", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/chicken_wrap.jpg"},
        {"name": "Tuna Sandwich", "price": 250.0, "description": "Fresh tuna sandwich with mayo", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/tuna_sandwich.jpg"},
        {"name": "Veggie Wrap", "price": 220.0, "description": "Healthy vegetable wrap", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/veggie_wrap.jpg"},
        {"name": "Beef Wrap", "price": 350.0, "description": "Tender beef wrap with sauce", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/beef_wrap.jpg"},
        
        # PIZZA CATEGORY (6 items)
        {"name": "Margherita Pizza", "price": 450.0, "description": "Classic pizza with tomato and mozzarella", "category": "Pizza", "image_url": "/static/uploads/margherita_pizza.jpg"},
        {"name": "Pepperoni Pizza", "price": 520.0, "description": "Pizza with pepperoni and cheese", "category": "Pizza", "image_url": "/static/uploads/pepperoni_pizza.jpg"},
        {"name": "Meat Lovers Pizza", "price": 680.0, "description": "Pizza loaded with assorted meats", "category": "Pizza", "image_url": "/static/uploads/meat_lovers_pizza.jpg"},
        {"name": "Vegetarian Pizza", "price": 420.0, "description": "Pizza with fresh vegetables", "category": "Pizza", "image_url": "/static/uploads/vegetarian_pizza.jpg"},
        {"name": "Hawaiian Pizza", "price": 480.0, "description": "Pizza with ham and pineapple", "category": "Pizza", "image_url": "/static/uploads/hawaiian_pizza.jpg"},
        {"name": "BBQ Chicken Pizza", "price": 550.0, "description": "Pizza with BBQ chicken and sauce", "category": "Pizza", "image_url": "/static/uploads/bbq_chicken_pizza.jpg"},
        
        # PASTA CATEGORY (4 items)
        {"name": "Spaghetti Bolognese", "price": 380.0, "description": "Classic spaghetti with meat sauce", "category": "Pasta", "image_url": "/static/uploads/spaghetti_bolognese.jpg"},
        {"name": "Fettuccine Alfredo", "price": 420.0, "description": "Creamy fettuccine with alfredo sauce", "category": "Pasta", "image_url": "/static/uploads/fettuccine_alfredo.jpg"},
        {"name": "Penne Arrabbiata", "price": 350.0, "description": "Spicy penne pasta with tomato sauce", "category": "Pasta", "image_url": "/static/uploads/penne_arrabbiata.jpg"},
        {"name": "Lasagna", "price": 480.0, "description": "Layered pasta with meat and cheese", "category": "Pasta", "image_url": "/static/uploads/lasagna.jpg"},
        
        # BURRITO CATEGORY (3 items)
        {"name": "Chicken Burrito", "price": 380.0, "description": "Wrapped tortilla with chicken and rice", "category": "Borrito", "image_url": "/static/uploads/chicken_burrito.jpg"},
        {"name": "Beef Burrito", "price": 420.0, "description": "Wrapped tortilla with beef and beans", "category": "Borrito", "image_url": "/static/uploads/beef_burrito.jpg"},
        {"name": "Veggie Burrito", "price": 320.0, "description": "Healthy vegetarian burrito", "category": "Borrito", "image_url": "/static/uploads/veggie_burrito.jpg"},
        
        # RICE DISHES CATEGORY (4 items)
        {"name": "Chicken Fried Rice", "price": 280.0, "description": "Fried rice with chicken and vegetables", "category": "Rice Dishes", "image_url": "/static/uploads/chicken_fried_rice.jpg"},
        {"name": "Beef Fried Rice", "price": 320.0, "description": "Fried rice with beef and spices", "category": "Rice Dishes", "image_url": "/static/uploads/beef_fried_rice.jpg"},
        {"name": "Vegetable Rice", "price": 220.0, "description": "Healthy rice with mixed vegetables", "category": "Rice Dishes", "image_url": "/static/uploads/vegetable_rice.jpg"},
        {"name": "Shrimp Rice", "price": 380.0, "description": "Rice with fresh shrimp", "category": "Rice Dishes", "image_url": "/static/uploads/shrimp_rice.jpg"},
        
        # EGG DISHES & TOAST CATEGORY (5 items)
        {"name": "Scrambled Eggs", "price": 150.0, "description": "Fluffy scrambled eggs", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/scrambled_eggs.jpg"},
        {"name": "Fried Eggs", "price": 120.0, "description": "Sunny side up fried eggs", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/fried_eggs.jpg"},
        {"name": "Omelette", "price": 180.0, "description": "Cheese and vegetable omelette", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/omelette.jpg"},
        {"name": "French Toast", "price": 200.0, "description": "Sweet French toast with syrup", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/french_toast.jpg"},
        {"name": "Avocado Toast", "price": 250.0, "description": "Toast with fresh avocado", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/avocado_toast.jpg"},
        
        # FRIES & PANCAKES CATEGORY (4 items)
        {"name": "French Fries", "price": 120.0, "description": "Crispy golden french fries", "category": "Fries & Pancakes", "image_url": "/static/uploads/french_fries.jpg"},
        {"name": "Sweet Potato Fries", "price": 150.0, "description": "Healthy sweet potato fries", "category": "Fries & Pancakes", "image_url": "/static/uploads/sweet_potato_fries.jpg"},
        {"name": "Pancakes", "price": 180.0, "description": "Fluffy pancakes with syrup", "category": "Fries & Pancakes", "image_url": "/static/uploads/pancakes.jpg"},
        {"name": "Loaded Fries", "price": 220.0, "description": "Fries with cheese and bacon", "category": "Fries & Pancakes", "image_url": "/static/uploads/loaded_fries.jpg"},
        
        # TRADITIONAL ETHIOPIAN BREAKFAST CATEGORY (6 items)
        {"name": "Ful", "price": 120.0, "description": "Traditional Ethiopian fava bean dish", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/ful.jpg"},
        {"name": "Kinche", "price": 100.0, "description": "Ethiopian cracked wheat porridge", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/kinche.jpg"},
        {"name": "Genfo", "price": 90.0, "description": "Ethiopian barley porridge", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/genfo.jpg"},
        {"name": "Chechebsa", "price": 130.0, "description": "Ethiopian flatbread with spices", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/chechebsa.jpg"},
        {"name": "Firfir", "price": 160.0, "description": "Spiced injera with berbere", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/firfir.jpg"},
        {"name": "Kitfo", "price": 280.0, "description": "Ethiopian beef tartare", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/kitfo.jpg"},
        
        # EXTRAS CATEGORY (4 items)
        {"name": "Bread Roll", "price": 50.0, "description": "Fresh baked bread roll", "category": "Extras", "image_url": "/static/uploads/bread_roll.jpg"},
        {"name": "Garlic Bread", "price": 80.0, "description": "Toasted garlic bread", "category": "Extras", "image_url": "/static/uploads/garlic_bread.jpg"},
        {"name": "Salad", "price": 120.0, "description": "Fresh mixed salad", "category": "Extras", "image_url": "/static/uploads/salad.jpg"},
        {"name": "Soup", "price": 100.0, "description": "Daily soup special", "category": "Extras", "image_url": "/static/uploads/soup.jpg"},
        
        # DRINKS CATEGORY (6 items)
        {"name": "Ethiopian Coffee", "price": 80.0, "description": "Traditional Ethiopian coffee", "category": "Drinks", "image_url": "/static/uploads/coffee.jpg"},
        {"name": "Fresh Juice", "price": 120.0, "description": "Freshly squeezed fruit juice", "category": "Drinks", "image_url": "/static/uploads/juice.jpg"},
        {"name": "Soft Drink", "price": 60.0, "description": "Carbonated soft drink", "category": "Drinks", "image_url": "/static/uploads/soft_drink.jpg"},
        {"name": "Tea", "price": 50.0, "description": "Hot tea", "category": "Drinks", "image_url": "/static/uploads/tea.jpg"},
        {"name": "Smoothie", "price": 150.0, "description": "Fresh fruit smoothie", "category": "Drinks", "image_url": "/static/uploads/smoothie.jpg"},
        {"name": "Water", "price": 30.0, "description": "Bottled water", "category": "Drinks", "image_url": "/static/uploads/water.jpg"},
        
        # SNACKS CATEGORY (4 items)
        {"name": "Popcorn", "price": 80.0, "description": "Buttery popcorn", "category": "Snacks", "image_url": "/static/uploads/popcorn.jpg"},
        {"name": "Chips", "price": 60.0, "description": "Crispy potato chips", "category": "Snacks", "image_url": "/static/uploads/chips.jpg"},
        {"name": "Nuts", "price": 100.0, "description": "Mixed nuts", "category": "Snacks", "image_url": "/static/uploads/nuts.jpg"},
        {"name": "Cookies", "price": 90.0, "description": "Freshly baked cookies", "category": "Snacks", "image_url": "/static/uploads/cookies.jpg"},
        
        # SAUCES CATEGORY (6 items)
        {"name": "Ketchup", "price": 20.0, "description": "Tomato ketchup", "category": "Sauces", "image_url": "/static/uploads/ketchup.jpg"},
        {"name": "Mustard", "price": 20.0, "description": "Yellow mustard", "category": "Sauces", "image_url": "/static/uploads/mustard.jpg"},
        {"name": "Mayo", "price": 25.0, "description": "Creamy mayonnaise", "category": "Sauces", "image_url": "/static/uploads/mayo.jpg"},
        {"name": "Hot Sauce", "price": 30.0, "description": "Spicy hot sauce", "category": "Sauces", "image_url": "/static/uploads/hot_sauce.jpg"},
        {"name": "BBQ Sauce", "price": 35.0, "description": "Sweet BBQ sauce", "category": "Sauces", "image_url": "/static/uploads/bbq_sauce.jpg"},
        {"name": "Ranch", "price": 40.0, "description": "Creamy ranch dressing", "category": "Sauces", "image_url": "/static/uploads/ranch.jpg"}
    ]
    
    # Create menu items with restaurant assignment
    for item_data in complete_menu:
        # Find the category
        category = Category.query.filter_by(name=item_data["category"]).first()
        if category:
            # Create menu item with restaurant_id
            menu_item = MenuItem(
                name=item_data["name"],
                price=item_data["price"],
                description=item_data["description"],
                category=item_data["category"],
                restaurant_id=1,  # Assign to X Factory restaurant
                image_url=item_data["image_url"],
                available=True
            )
            db.session.add(menu_item)
    
    db.session.commit()
    print(f"Created {len(complete_menu)} complete menu items across all categories")

if __name__ == "__main__":
    initialize_database()