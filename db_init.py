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
    """Create default menu items"""
    # Sample menu items for testing
    sample_items = [
        # Burgers
        {"name": "Beef Burger Normal", "price": 400.0, "description": "Delicious beef burger with classic toppings", "category": "Burgers", "image_url": "/static/uploads/beef_burger_normal.jpg"},
        {"name": "Chicken Burger Special", "price": 540.0, "description": "Premium chicken burger with special sauce", "category": "Burgers", "image_url": "/static/uploads/chicken_burger_special.jpg"},
        
        # Shawarma
        {"name": "Beef Shawarma Large", "price": 495.0, "description": "Large beef shawarma with traditional spices", "category": "Shawarma", "image_url": "/static/uploads/beef_shawarma_large.jpg"},
        {"name": "Chicken Shawarma Small", "price": 430.0, "description": "Small chicken shawarma with authentic taste", "category": "Shawarma", "image_url": "/static/uploads/chicken_shawarma_small.jpg"},
        
        # Traditional Ethiopian Breakfast
        {"name": "Ful", "price": 120.0, "description": "Traditional Ethiopian fava bean dish", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/ful.jpg"},
        {"name": "Kinche", "price": 100.0, "description": "Ethiopian cracked wheat porridge", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/kinche.jpg"},
        
        # Drinks
        {"name": "Ethiopian Coffee", "price": 80.0, "description": "Traditional Ethiopian coffee", "category": "Drinks", "image_url": "/static/uploads/coffee.jpg"},
        {"name": "Fresh Juice", "price": 120.0, "description": "Freshly squeezed fruit juice", "category": "Drinks", "image_url": "/static/uploads/juice.jpg"}
    ]
    
    for item_data in sample_items:
        menu_item = MenuItem(**item_data)
        db.session.add(menu_item)
    
    db.session.commit()
    print(f"Created {len(sample_items)} default menu items")

if __name__ == "__main__":
    initialize_database()