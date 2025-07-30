"""
Restaurant Kitchen Setup System
Handles creation of new restaurants with default 14 categories and 64 food products
"""

from app import app, db
from models import Restaurant, Category, MenuItem, AdminUser
from datetime import datetime

def create_new_restaurant_kitchen(restaurant_name, admin_user_id=None):
    """
    Create a new restaurant with default categories and menu items
    """
    with app.app_context():
        # Create new restaurant
        restaurant = Restaurant(
            name=restaurant_name,
            description=f'{restaurant_name} - Premium food delivery service',
            address='Addis Ababa, Ethiopia',
            phone='+251911000000',
            latitude=9.047658,
            longitude=38.741143,
            is_active=True,
            is_featured=False,
            delivery_fee=50.0,
            minimum_order=200.0,
            estimated_delivery_time='30-45 minutes',
            opening_hours={
                'monday': '09:00-22:00',
                'tuesday': '09:00-22:00',
                'wednesday': '09:00-22:00',
                'thursday': '09:00-22:00',
                'friday': '09:00-22:00',
                'saturday': '09:00-22:00',
                'sunday': '09:00-22:00'
            }
        )
        
        db.session.add(restaurant)
        db.session.commit()
        
        # Create default categories for this restaurant
        create_default_categories_for_restaurant(restaurant.id, admin_user_id)
        
        # Create default menu items for this restaurant
        create_default_menu_items_for_restaurant(restaurant.id, admin_user_id)
        
        return restaurant

def create_default_categories_for_restaurant(restaurant_id, admin_user_id=None):
    """Create 14 default categories for a restaurant"""
    
    default_categories = [
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
    
    for cat_data in default_categories:
        category = Category(
            name=cat_data["name"],
            description=cat_data["description"],
            icon=cat_data["icon"],
            sort_order=cat_data["sort_order"],
            restaurant_id=restaurant_id,
            created_by=admin_user_id,
            is_active=True
        )
        db.session.add(category)
    
    db.session.commit()
    return len(default_categories)

def create_default_menu_items_for_restaurant(restaurant_id, admin_user_id=None):
    """Create 64 default menu items for a restaurant"""
    
    default_menu_items = [
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
        {"name": "Margherita Pizza", "price": 650.0, "description": "Classic Italian pizza with tomato and mozzarella", "category": "Pizza", "image_url": "/static/uploads/margherita_pizza.jpg"},
        {"name": "Pepperoni Pizza", "price": 750.0, "description": "Spicy pepperoni pizza with extra cheese", "category": "Pizza", "image_url": "/static/uploads/pepperoni_pizza.jpg"},
        {"name": "Vegetarian Pizza", "price": 680.0, "description": "Fresh vegetable pizza with mixed toppings", "category": "Pizza", "image_url": "/static/uploads/vegetarian_pizza.jpg"},
        {"name": "Meat Lovers Pizza", "price": 850.0, "description": "Pizza loaded with various meats", "category": "Pizza", "image_url": "/static/uploads/meat_lovers_pizza.jpg"},
        {"name": "Hawaiian Pizza", "price": 720.0, "description": "Pizza with ham and pineapple", "category": "Pizza", "image_url": "/static/uploads/hawaiian_pizza.jpg"},
        {"name": "BBQ Chicken Pizza", "price": 780.0, "description": "BBQ chicken pizza with special sauce", "category": "Pizza", "image_url": "/static/uploads/bbq_chicken_pizza.jpg"},
        
        # PASTA CATEGORY (4 items)
        {"name": "Spaghetti Bolognese", "price": 450.0, "description": "Classic Italian pasta with meat sauce", "category": "Pasta", "image_url": "/static/uploads/spaghetti_bolognese.jpg"},
        {"name": "Chicken Alfredo", "price": 520.0, "description": "Creamy chicken alfredo pasta", "category": "Pasta", "image_url": "/static/uploads/chicken_alfredo.jpg"},
        {"name": "Penne Arrabbiata", "price": 380.0, "description": "Spicy tomato pasta with herbs", "category": "Pasta", "image_url": "/static/uploads/penne_arrabbiata.jpg"},
        {"name": "Seafood Pasta", "price": 650.0, "description": "Mixed seafood pasta with white sauce", "category": "Pasta", "image_url": "/static/uploads/seafood_pasta.jpg"},
        
        # BORRITO CATEGORY (3 items)
        {"name": "Chicken Burrito", "price": 420.0, "description": "Grilled chicken burrito with rice and beans", "category": "Borrito", "image_url": "/static/uploads/chicken_burrito.jpg"},
        {"name": "Beef Burrito", "price": 480.0, "description": "Seasoned beef burrito with vegetables", "category": "Borrito", "image_url": "/static/uploads/beef_burrito.jpg"},
        {"name": "Vegetarian Burrito", "price": 350.0, "description": "Healthy vegetarian burrito with beans", "category": "Borrito", "image_url": "/static/uploads/vegetarian_burrito.jpg"},
        
        # RICE DISHES CATEGORY (4 items)
        {"name": "Chicken Fried Rice", "price": 380.0, "description": "Stir-fried rice with chicken and vegetables", "category": "Rice Dishes", "image_url": "/static/uploads/chicken_fried_rice.jpg"},
        {"name": "Vegetable Rice", "price": 320.0, "description": "Healthy vegetable rice with mixed veggies", "category": "Rice Dishes", "image_url": "/static/uploads/vegetable_rice.jpg"},
        {"name": "Beef Rice Bowl", "price": 450.0, "description": "Tender beef over seasoned rice", "category": "Rice Dishes", "image_url": "/static/uploads/beef_rice_bowl.jpg"},
        {"name": "Seafood Rice", "price": 550.0, "description": "Mixed seafood rice with special sauce", "category": "Rice Dishes", "image_url": "/static/uploads/seafood_rice.jpg"},
        
        # EGG DISHES & TOAST CATEGORY (5 items)
        {"name": "Scrambled Eggs", "price": 180.0, "description": "Fluffy scrambled eggs with toast", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/scrambled_eggs.jpg"},
        {"name": "Fried Eggs", "price": 160.0, "description": "Sunny-side up eggs with toast", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/fried_eggs.jpg"},
        {"name": "Omelette", "price": 220.0, "description": "Cheese omelette with vegetables", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/omelette.jpg"},
        {"name": "French Toast", "price": 200.0, "description": "Sweet French toast with syrup", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/french_toast.jpg"},
        {"name": "Egg Benedict", "price": 280.0, "description": "Poached eggs with hollandaise sauce", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/egg_benedict.jpg"},
        
        # FRIES & PANCAKES CATEGORY (4 items)
        {"name": "French Fries", "price": 150.0, "description": "Crispy golden French fries", "category": "Fries & Pancakes", "image_url": "/static/uploads/french_fries.jpg"},
        {"name": "Sweet Potato Fries", "price": 180.0, "description": "Healthy sweet potato fries", "category": "Fries & Pancakes", "image_url": "/static/uploads/sweet_potato_fries.jpg"},
        {"name": "Pancakes", "price": 250.0, "description": "Fluffy pancakes with syrup", "category": "Fries & Pancakes", "image_url": "/static/uploads/pancakes.jpg"},
        {"name": "Loaded Fries", "price": 220.0, "description": "Fries with cheese and bacon", "category": "Fries & Pancakes", "image_url": "/static/uploads/loaded_fries.jpg"},
        
        # TRADITIONAL ETHIOPIAN BREAKFAST CATEGORY (6 items)
        {"name": "Firfir", "price": 200.0, "description": "Traditional Ethiopian breakfast with injera", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/firfir.jpg"},
        {"name": "Ful", "price": 180.0, "description": "Ethiopian fava bean dish", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/ful.jpg"},
        {"name": "Genfo", "price": 150.0, "description": "Traditional Ethiopian porridge", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/genfo.jpg"},
        {"name": "Kita Firfir", "price": 220.0, "description": "Firfir with kita bread", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/kita_firfir.jpg"},
        {"name": "Chechebsa", "price": 160.0, "description": "Spicy Ethiopian pancake", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/chechebsa.jpg"},
        {"name": "Ethiopian Coffee", "price": 80.0, "description": "Traditional Ethiopian coffee ceremony", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/ethiopian_coffee.jpg"},
        
        # EXTRAS CATEGORY (4 items)
        {"name": "Salad", "price": 120.0, "description": "Fresh mixed green salad", "category": "Extras", "image_url": "/static/uploads/salad.jpg"},
        {"name": "Soup", "price": 100.0, "description": "Daily soup special", "category": "Extras", "image_url": "/static/uploads/soup.jpg"},
        {"name": "Bread", "price": 60.0, "description": "Fresh baked bread", "category": "Extras", "image_url": "/static/uploads/bread.jpg"},
        {"name": "Garlic Bread", "price": 80.0, "description": "Toasted garlic bread", "category": "Extras", "image_url": "/static/uploads/garlic_bread.jpg"},
        
        # DRINKS CATEGORY (6 items)
        {"name": "Coca Cola", "price": 80.0, "description": "Classic Coca Cola", "category": "Drinks", "image_url": "/static/uploads/coca_cola.jpg"},
        {"name": "Sprite", "price": 80.0, "description": "Refreshing Sprite", "category": "Drinks", "image_url": "/static/uploads/sprite.jpg"},
        {"name": "Orange Juice", "price": 100.0, "description": "Fresh orange juice", "category": "Drinks", "image_url": "/static/uploads/orange_juice.jpg"},
        {"name": "Apple Juice", "price": 100.0, "description": "Fresh apple juice", "category": "Drinks", "image_url": "/static/uploads/apple_juice.jpg"},
        {"name": "Water", "price": 40.0, "description": "Pure drinking water", "category": "Drinks", "image_url": "/static/uploads/water.jpg"},
        {"name": "Coffee", "price": 60.0, "description": "Fresh brewed coffee", "category": "Drinks", "image_url": "/static/uploads/coffee.jpg"},
        
        # SNACKS CATEGORY (4 items)
        {"name": "Chips", "price": 90.0, "description": "Crispy potato chips", "category": "Snacks", "image_url": "/static/uploads/chips.jpg"},
        {"name": "Popcorn", "price": 70.0, "description": "Buttery popcorn", "category": "Snacks", "image_url": "/static/uploads/popcorn.jpg"},
        {"name": "Nuts", "price": 120.0, "description": "Mixed nuts", "category": "Snacks", "image_url": "/static/uploads/nuts.jpg"},
        {"name": "Cookies", "price": 80.0, "description": "Chocolate chip cookies", "category": "Snacks", "image_url": "/static/uploads/cookies.jpg"},
        
        # SAUCES CATEGORY (6 items)
        {"name": "Ketchup", "price": 20.0, "description": "Tomato ketchup", "category": "Sauces", "image_url": "/static/uploads/ketchup.jpg"},
        {"name": "Mayonnaise", "price": 25.0, "description": "Creamy mayonnaise", "category": "Sauces", "image_url": "/static/uploads/mayonnaise.jpg"},
        {"name": "Mustard", "price": 20.0, "description": "Yellow mustard", "category": "Sauces", "image_url": "/static/uploads/mustard.jpg"},
        {"name": "BBQ Sauce", "price": 30.0, "description": "Smoky BBQ sauce", "category": "Sauces", "image_url": "/static/uploads/bbq_sauce.jpg"},
        {"name": "Hot Sauce", "price": 25.0, "description": "Spicy hot sauce", "category": "Sauces", "image_url": "/static/uploads/hot_sauce.jpg"},
        {"name": "Garlic Sauce", "price": 30.0, "description": "Creamy garlic sauce", "category": "Sauces", "image_url": "/static/uploads/garlic_sauce.jpg"}
    ]
    
    for item_data in default_menu_items:
        menu_item = MenuItem(
            name=item_data["name"],
            price=item_data["price"],
            description=item_data["description"],
            category=item_data["category"],
            image_url=item_data["image_url"],
            restaurant_id=restaurant_id,
            available=True
        )
        db.session.add(menu_item)
    
    db.session.commit()
    return len(default_menu_items)

def setup_food_availability_system():
    """
    Set up the food availability notification system for customers
    """
    # This will be handled in the order processing system
    pass

if __name__ == "__main__":
    # Initialize X Factory restaurant with default data
    with app.app_context():
        db.create_all()
        
        # Check if X Factory already exists
        existing_restaurant = Restaurant.query.filter_by(name="X Factory").first()
        if not existing_restaurant:
            restaurant = create_new_restaurant_kitchen("X Factory")
            print(f"Created restaurant: {restaurant.name}")
            print(f"Created 14 categories")
            print(f"Created 64 menu items")
        else:
            print("X Factory restaurant already exists")