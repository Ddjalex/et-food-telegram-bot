#!/usr/bin/env python3
"""
Initialize ET-FOOD system with required data
"""
import os
import sys
from app import app, db
from models import AdminUser, Restaurant, MenuItem, Category
from werkzeug.security import generate_password_hash

def create_super_admin():
    """Create super admin user"""
    print("🔐 Creating super admin user...")
    
    # Check if super admin already exists
    existing_admin = AdminUser.query.filter_by(username='superadmin').first()
    if existing_admin:
        print("⚠️  Super admin 'superadmin' already exists, updating password...")
        existing_admin.password_hash = generate_password_hash('admin123')
        existing_admin.role = 'super_admin'
        existing_admin.is_active = True
        existing_admin.is_approved = True
        db.session.commit()
        print("✅ Updated existing super admin password to 'admin123'")
        return existing_admin
    
    # Create new super admin
    super_admin = AdminUser(
        username='superadmin',
        email='superadmin@etfood.com',
        full_name='Super Administrator',
        password_hash=generate_password_hash('admin123'),
        role='super_admin',
        is_active=True,
        is_approved=True,
        restaurant_id=None  # Super admin not tied to specific restaurant
    )
    
    db.session.add(super_admin)
    db.session.commit()
    
    print("✅ Super admin created successfully!")
    print("   Username: superadmin")
    print("   Password: admin123")
    print("   Role: super_admin")
    return super_admin

def create_menu_items():
    """Create menu items for restaurants"""
    print("🍔 Creating menu items...")
    
    # Get restaurants
    flavour_cafe = Restaurant.query.filter_by(name='Flavour cafe | E.Fabrica').first()
    y_factory = Restaurant.query.filter_by(name='Y Factory Restaurant').first()
    
    if not flavour_cafe or not y_factory:
        print("❌ Restaurants not found")
        return
    
    # Sample menu items with authentic Ethiopian and international cuisine
    menu_items = [
        # Ethiopian Traditional Dishes
        {
            'name': 'Injera with Doro Wat',
            'price': 180.0,
            'description': 'Traditional Ethiopian sourdough flatbread served with spicy chicken stew',
            'category': 'ethiopian',
            'image_url': '/static/uploads/1751975047_images_25.jpg',
            'restaurant_id': flavour_cafe.id
        },
        {
            'name': 'Kitfo',
            'price': 200.0,
            'description': 'Ethiopian steak tartare seasoned with mitmita and served with cottage cheese',
            'category': 'ethiopian',
            'image_url': '/static/uploads/1751975080_images_26.jpg',
            'restaurant_id': flavour_cafe.id
        },
        {
            'name': 'Tibs',
            'price': 160.0,
            'description': 'Sautéed beef or lamb with onions, tomatoes, and Ethiopian spices',
            'category': 'ethiopian',
            'image_url': '/static/uploads/1751975388_images_28.jpg',
            'restaurant_id': flavour_cafe.id
        },
        {
            'name': 'Shiro Wat',
            'price': 120.0,
            'description': 'Traditional Ethiopian chickpea flour stew with berbere spice',
            'category': 'ethiopian',
            'image_url': '/static/uploads/1751975114_images_27.jpg',
            'restaurant_id': flavour_cafe.id
        },
        
        # International Cuisine
        {
            'name': 'Classic Beef Burger',
            'price': 150.0,
            'description': 'Juicy beef patty with lettuce, tomato, onion, and special sauce',
            'category': 'burgers',
            'image_url': '/static/uploads/1751975959_Screen-Shot-2015-08-14-at-5.39.07-PM.webp',
            'restaurant_id': flavour_cafe.id
        },
        {
            'name': 'Chicken Shawarma',
            'price': 130.0,
            'description': 'Tender chicken shawarma with vegetables and tahini sauce',
            'category': 'sandwiches',
            'image_url': '/static/uploads/1751976242_images_35.jpg',
            'restaurant_id': flavour_cafe.id
        },
        {
            'name': 'Margherita Pizza',
            'price': 170.0,
            'description': 'Fresh mozzarella, tomato sauce, and basil on crispy crust',
            'category': 'pizza',
            'image_url': '/static/uploads/1751976307_IMG_0282-scaled-1.jpg',
            'restaurant_id': flavour_cafe.id
        },
        {
            'name': 'Pasta Carbonara',
            'price': 140.0,
            'description': 'Creamy pasta with bacon, eggs, and parmesan cheese',
            'category': 'pasta',
            'image_url': '/static/uploads/1751975863_images_33.jpg',
            'restaurant_id': flavour_cafe.id
        },
        
        # Beverages
        {
            'name': 'Ethiopian Coffee',
            'price': 40.0,
            'description': 'Traditional Ethiopian coffee ceremony style',
            'category': 'drinks',
            'image_url': '/static/uploads/1751976624_vegan-breakfast.jpg',
            'restaurant_id': flavour_cafe.id
        },
        {
            'name': 'Fresh Orange Juice',
            'price': 35.0,
            'description': 'Freshly squeezed orange juice',
            'category': 'drinks',
            'image_url': '/static/placeholder-food.jpg',
            'restaurant_id': flavour_cafe.id
        },
        
        # Y Factory Restaurant items
        {
            'name': 'Grilled Chicken Breast',
            'price': 180.0,
            'description': 'Tender grilled chicken breast with vegetables',
            'category': 'main_courses',
            'image_url': '/static/placeholder-food.jpg',
            'restaurant_id': y_factory.id
        },
        {
            'name': 'Fish and Chips',
            'price': 160.0,
            'description': 'Crispy battered fish with golden fries',
            'category': 'main_courses',
            'image_url': '/static/placeholder-food.jpg',
            'restaurant_id': y_factory.id
        }
    ]
    
    # Clear existing menu items
    MenuItem.query.delete()
    db.session.commit()
    
    # Add new menu items
    for item_data in menu_items:
        menu_item = MenuItem(**item_data)
        db.session.add(menu_item)
    
    db.session.commit()
    print(f"✅ Created {len(menu_items)} menu items")

def create_categories():
    """Create menu categories"""
    print("📋 Creating menu categories...")
    
    # Get restaurants
    restaurants = Restaurant.query.all()
    
    categories_data = [
        {'name': 'Ethiopian', 'description': 'Traditional Ethiopian dishes', 'icon': '🇪🇹'},
        {'name': 'Burgers', 'description': 'Delicious burgers and sandwiches', 'icon': '🍔'},
        {'name': 'Pizza', 'description': 'Wood-fired pizzas', 'icon': '🍕'},
        {'name': 'Pasta', 'description': 'Italian pasta dishes', 'icon': '🍝'},
        {'name': 'Drinks', 'description': 'Beverages and drinks', 'icon': '🥤'},
        {'name': 'Main Courses', 'description': 'Main course dishes', 'icon': '🍽️'},
        {'name': 'Sandwiches', 'description': 'Wraps and sandwiches', 'icon': '🥪'},
    ]
    
    # Clear existing categories
    Category.query.delete()
    db.session.commit()
    
    # Add categories for each restaurant
    for restaurant in restaurants:
        for cat_data in categories_data:
            category = Category(
                name=cat_data['name'],
                description=cat_data['description'],
                icon=cat_data['icon'],
                restaurant_id=restaurant.id
            )
            db.session.add(category)
    
    db.session.commit()
    print(f"✅ Created categories for {len(restaurants)} restaurants")

def initialize_system():
    """Initialize the complete system"""
    print("🚀 Initializing ET-FOOD system...")
    
    with app.app_context():
        try:
            # Ensure all tables exist
            db.create_all()
            
            # Create super admin
            admin = create_super_admin()
            
            # Create categories
            create_categories()
            
            # Create menu items
            create_menu_items()
            
            print("\n🎉 System initialization completed successfully!")
            print("\n📝 Login Credentials:")
            print("   Super Admin:")
            print("   - URL: /superadmin/login")
            print("   - Username: superadmin")
            print("   - Password: admin123")
            print("\n🍽️ Restaurants Available:")
            restaurants = Restaurant.query.all()
            for restaurant in restaurants:
                item_count = MenuItem.query.filter_by(restaurant_id=restaurant.id).count()
                print(f"   - {restaurant.name}: {item_count} menu items")
            
        except Exception as e:
            print(f"❌ Error during initialization: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    initialize_system()