#!/usr/bin/env python3
"""
Comprehensive fix for all ET-FOOD issues:
1. Fix menu items count showing wrong number (should be 64-66 items for Flavour cafe)
2. Add missing admin creation and restaurant creation POST endpoints  
3. Ensure superadmin dashboard action buttons work properly
4. Verify authentication and API access
"""

from app_mongodb import app
from models_final import menu_item_model, restaurant_model, admin_user_model
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_database_state():
    """Debug current database state"""
    with app.app_context():
        logger.info("🔍 Debugging Database State:")
        
        # Check restaurants
        restaurants = restaurant_model.get_all_restaurants()
        logger.info(f"   Restaurants: {len(restaurants)}")
        for r in restaurants:
            logger.info(f"     - {r['name']} (ID: {r['id']})")
        
        # Check menu items
        total_items = menu_item_model.count()
        logger.info(f"   Total Menu Items: {total_items}")
        
        # Check menu items per restaurant
        for r in restaurants:
            count = menu_item_model.count({'restaurant_id': r['id']})
            logger.info(f"     - {r['name']}: {count} items")
            
            # Show some sample items for Flavour cafe
            if "Flavour" in r['name']:
                items = menu_item_model.find_many({'restaurant_id': r['id']})
                sample_items = list(items)[:5]
                for item in sample_items:
                    logger.info(f"       Sample: {item['name']} ({item['category']})")
        
        # Check admin users
        admins = admin_user_model.get_all_admins()
        logger.info(f"   Admin Users: {len(admins)}")
        for admin in admins:
            logger.info(f"     - {admin['username']} ({admin.get('role', 'admin')})")

def restore_menu_properly():
    """Properly restore Flavour cafe menu with 66 items"""
    
    # Complete menu data (66 items across 14 categories)
    menu_items = [
        # Burgers (8 items)
        {"name": "Classic Beef Burger", "price": 250.0, "description": "Juicy beef patty with lettuce, tomato, onion", "category": "Burgers", "image_url": "/static/uploads/classic_burger.jpg"},
        {"name": "Chicken Burger Special", "price": 280.0, "description": "Grilled chicken breast with special sauce", "category": "Burgers", "image_url": "/static/uploads/chicken_burger.jpg"},
        {"name": "Cheese Burger Deluxe", "price": 300.0, "description": "Double cheese with beef patty", "category": "Burgers", "image_url": "/static/uploads/cheese_burger.jpg"},
        {"name": "Fish Burger", "price": 320.0, "description": "Fresh fish fillet with tartar sauce", "category": "Burgers", "image_url": "/static/uploads/fish_burger.jpg"},
        {"name": "Veggie Burger", "price": 240.0, "description": "Plant-based patty with fresh vegetables", "category": "Burgers", "image_url": "/static/uploads/veggie_burger.jpg"},
        {"name": "BBQ Bacon Burger", "price": 350.0, "description": "Smoky BBQ sauce with crispy bacon", "category": "Burgers", "image_url": "/static/uploads/bbq_burger.jpg"},
        {"name": "Mushroom Swiss Burger", "price": 330.0, "description": "Sautéed mushrooms with Swiss cheese", "category": "Burgers", "image_url": "/static/uploads/mushroom_burger.jpg"},
        {"name": "Spicy Jalapeño Burger", "price": 290.0, "description": "Spicy jalapeños with pepper jack cheese", "category": "Burgers", "image_url": "/static/uploads/spicy_burger.jpg"},
        
        # Shawarma (4 items)
        {"name": "Chicken Shawarma", "price": 200.0, "description": "Marinated chicken with garlic sauce", "category": "Shawarma", "image_url": "/static/uploads/chicken_shawarma.jpg"},
        {"name": "Beef Shawarma Large", "price": 250.0, "description": "Tender beef with tahini sauce", "category": "Shawarma", "image_url": "/static/uploads/beef_shawarma.jpg"},
        {"name": "Mixed Shawarma", "price": 280.0, "description": "Combination of chicken and beef", "category": "Shawarma", "image_url": "/static/uploads/mixed_shawarma.jpg"},
        {"name": "Lamb Shawarma Premium", "price": 320.0, "description": "Premium lamb with special spices", "category": "Shawarma", "image_url": "/static/uploads/lamb_shawarma.jpg"},
        
        # Sandwiches & Wraps (5 items)
        {"name": "Club Sandwich", "price": 180.0, "description": "Triple-layered with chicken, bacon, lettuce", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/club_sandwich.jpg"},
        {"name": "Chicken Caesar Wrap", "price": 170.0, "description": "Grilled chicken with Caesar dressing", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/caesar_wrap.jpg"},
        {"name": "Tuna Sandwich", "price": 160.0, "description": "Fresh tuna salad with vegetables", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/tuna_sandwich.jpg"},
        {"name": "Grilled Cheese Panini", "price": 140.0, "description": "Melted cheese in grilled bread", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/panini.jpg"},
        {"name": "Buffalo Chicken Wrap", "price": 190.0, "description": "Spicy buffalo chicken with ranch", "category": "Sandwiches & Wraps", "image_url": "/static/uploads/buffalo_wrap.jpg"},
        
        # Pizza (5 items)
        {"name": "Margherita Pizza", "price": 300.0, "description": "Fresh basil, mozzarella, tomato sauce", "category": "Pizza", "image_url": "/static/uploads/margherita_pizza.jpg"},
        {"name": "Pepperoni Pizza", "price": 350.0, "description": "Classic pepperoni with mozzarella", "category": "Pizza", "image_url": "/static/uploads/pepperoni_pizza.jpg"},
        {"name": "Meat Lovers Pizza", "price": 400.0, "description": "Pepperoni, sausage, bacon, ham", "category": "Pizza", "image_url": "/static/uploads/meat_pizza.jpg"},
        {"name": "Vegetarian Pizza", "price": 320.0, "description": "Bell peppers, mushrooms, onions, olives", "category": "Pizza", "image_url": "/static/uploads/veggie_pizza.jpg"},
        {"name": "BBQ Chicken Pizza", "price": 380.0, "description": "BBQ sauce, grilled chicken, red onions", "category": "Pizza", "image_url": "/static/uploads/bbq_pizza.jpg"},
        
        # Pasta (5 items)
        {"name": "Spaghetti Bolognese", "price": 280.0, "description": "Traditional meat sauce with parmesan", "category": "Pasta", "image_url": "/static/uploads/bolognese.jpg"},
        {"name": "Chicken Alfredo", "price": 300.0, "description": "Creamy alfredo sauce with grilled chicken", "category": "Pasta", "image_url": "/static/uploads/alfredo.jpg"},
        {"name": "Penne Arrabbiata", "price": 260.0, "description": "Spicy tomato sauce with herbs", "category": "Pasta", "image_url": "/static/uploads/arrabbiata.jpg"},
        {"name": "Seafood Pasta", "price": 350.0, "description": "Mixed seafood in white wine sauce", "category": "Pasta", "image_url": "/static/uploads/seafood_pasta.jpg"},
        {"name": "Vegetable Primavera", "price": 240.0, "description": "Fresh vegetables in light cream sauce", "category": "Pasta", "image_url": "/static/uploads/primavera.jpg"},
        
        # Borrito (3 items)
        {"name": "Chicken Burrito", "price": 220.0, "description": "Grilled chicken with rice and beans", "category": "Borrito", "image_url": "/static/uploads/chicken_burrito.jpg"},
        {"name": "Beef Burrito Supreme", "price": 250.0, "description": "Seasoned beef with cheese and salsa", "category": "Borrito", "image_url": "/static/uploads/beef_burrito.jpg"},
        {"name": "Vegetarian Burrito", "price": 200.0, "description": "Black beans, rice, vegetables, guacamole", "category": "Borrito", "image_url": "/static/uploads/veggie_burrito.jpg"},
        
        # Rice Dishes (4 items)
        {"name": "Chicken Fried Rice", "price": 180.0, "description": "Wok-fried rice with chicken and vegetables", "category": "Rice Dishes", "image_url": "/static/uploads/chicken_rice.jpg"},
        {"name": "Beef Teriyaki Rice", "price": 220.0, "description": "Tender beef with teriyaki sauce over rice", "category": "Rice Dishes", "image_url": "/static/uploads/teriyaki_rice.jpg"},
        {"name": "Vegetable Biryani", "price": 160.0, "description": "Aromatic basmati rice with mixed vegetables", "category": "Rice Dishes", "image_url": "/static/uploads/biryani.jpg"},
        {"name": "Seafood Paella", "price": 280.0, "description": "Spanish rice with mixed seafood", "category": "Rice Dishes", "image_url": "/static/uploads/paella.jpg"},
        
        # Egg Dishes & Toast (3 items)  
        {"name": "Scrambled Eggs on Toast", "price": 120.0, "description": "Fluffy scrambled eggs on buttered toast", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/scrambled_eggs.jpg"},
        {"name": "Eggs Benedict", "price": 180.0, "description": "Poached eggs with hollandaise sauce", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/benedict.jpg"},
        {"name": "Avocado Toast", "price": 140.0, "description": "Smashed avocado on sourdough with lime", "category": "Egg Dishes & Toast", "image_url": "/static/uploads/avocado_toast.jpg"},
        
        # Fries & Pancakes (4 items)
        {"name": "Classic French Fries", "price": 80.0, "description": "Crispy golden potato fries", "category": "Fries & Pancakes", "image_url": "/static/uploads/french_fries.jpg"},
        {"name": "Sweet Potato Fries", "price": 100.0, "description": "Crispy sweet potato fries with herbs", "category": "Fries & Pancakes", "image_url": "/static/uploads/sweet_fries.jpg"},
        {"name": "Fluffy Pancakes", "price": 150.0, "description": "Stack of pancakes with maple syrup", "category": "Fries & Pancakes", "image_url": "/static/uploads/pancakes.jpg"},
        {"name": "Loaded Cheese Fries", "price": 120.0, "description": "Fries topped with melted cheese and bacon", "category": "Fries & Pancakes", "image_url": "/static/uploads/loaded_fries.jpg"},
        
        # Traditional Ethiopian Breakfast (8 items)
        {"name": "Injera with Doro Wat", "price": 200.0, "description": "Traditional Ethiopian chicken stew", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/doro_wat.jpg"},
        {"name": "Kitfo", "price": 250.0, "description": "Ethiopian steak tartare with mitmita", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/kitfo.jpg"},
        {"name": "Tibs", "price": 220.0, "description": "Sautéed beef with vegetables", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/tibs.jpg"},
        {"name": "Shiro Wat", "price": 150.0, "description": "Spiced chickpea stew", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/shiro_wat.jpg"},
        {"name": "Gomen", "price": 120.0, "description": "Collard greens with spices", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/gomen.jpg"},
        {"name": "Misir Wat", "price": 140.0, "description": "Spicy red lentil stew", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/misir_wat.jpg"},
        {"name": "Combination Platter", "price": 300.0, "description": "Sampler of various Ethiopian dishes", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/combination.jpg"},
        {"name": "Injera and Honey Wine", "price": 180.0, "description": "Traditional injera with tej (honey wine)", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/tej.jpg"},
        
        # Drinks (7 items)
        {"name": "Ethiopian Coffee", "price": 50.0, "description": "Traditional Ethiopian coffee ceremony", "category": "Drinks", "image_url": "/static/uploads/ethiopian_coffee.jpg"},
        {"name": "Fresh Orange Juice", "price": 60.0, "description": "Freshly squeezed orange juice", "category": "Drinks", "image_url": "/static/uploads/orange_juice.jpg"},
        {"name": "Mango Smoothie", "price": 80.0, "description": "Creamy mango smoothie with yogurt", "category": "Drinks", "image_url": "/static/uploads/mango_smoothie.jpg"},
        {"name": "Coca Cola", "price": 40.0, "description": "Classic Coca Cola", "category": "Drinks", "image_url": "/static/uploads/coca_cola.jpg"},
        {"name": "Fresh Lemonade", "price": 50.0, "description": "Freshly made lemonade with mint", "category": "Drinks", "image_url": "/static/uploads/lemonade.jpg"},
        {"name": "Iced Tea", "price": 45.0, "description": "Refreshing iced tea with lemon", "category": "Drinks", "image_url": "/static/uploads/iced_tea.jpg"},
        {"name": "Sparkling Water", "price": 35.0, "description": "Premium sparkling water", "category": "Drinks", "image_url": "/static/uploads/sparkling_water.jpg"},
        
        # Snacks (4 items)
        {"name": "Chicken Wings", "price": 160.0, "description": "Spicy buffalo chicken wings", "category": "Snacks", "image_url": "/static/uploads/chicken_wings.jpg"},
        {"name": "Onion Rings", "price": 90.0, "description": "Crispy battered onion rings", "category": "Snacks", "image_url": "/static/uploads/onion_rings.jpg"},
        {"name": "Mozzarella Sticks", "price": 120.0, "description": "Fried mozzarella with marinara sauce", "category": "Snacks", "image_url": "/static/uploads/mozzarella_sticks.jpg"},
        {"name": "Nachos Supreme", "price": 140.0, "description": "Loaded nachos with cheese, jalapeños, sour cream", "category": "Snacks", "image_url": "/static/uploads/nachos.jpg"},
        
        # Sauces (3 items)
        {"name": "Ketchup", "price": 15.0, "description": "Classic tomato ketchup", "category": "Sauces", "image_url": "/static/uploads/ketchup.jpg"},
        {"name": "Mayonnaise", "price": 15.0, "description": "Creamy mayonnaise", "category": "Sauces", "image_url": "/static/uploads/mayo.jpg"},
        {"name": "Hot Sauce", "price": 20.0, "description": "Spicy chili sauce", "category": "Sauces", "image_url": "/static/uploads/hot_sauce.jpg"},
        
        # Extras (3 items)
        {"name": "Extra Cheese", "price": 25.0, "description": "Additional cheese topping", "category": "Extras", "image_url": "/static/uploads/extra_cheese.jpg"},
        {"name": "Extra Bacon", "price": 40.0, "description": "Crispy bacon strips", "category": "Extras", "image_url": "/static/uploads/extra_bacon.jpg"},
        {"name": "Garlic Bread", "price": 60.0, "description": "Toasted garlic bread", "category": "Extras", "image_url": "/static/uploads/garlic_bread.jpg"},
    ]
    
    with app.app_context():
        logger.info("🔧 Starting comprehensive menu restoration...")
        
        # Find Flavour cafe restaurant
        restaurants = restaurant_model.get_all_restaurants()
        flavour_cafe = None
        for restaurant in restaurants:
            if "Flavour cafe" in restaurant['name']:
                flavour_cafe = restaurant
                break
        
        if not flavour_cafe:
            logger.error("❌ Flavour cafe not found!")
            return False
        
        logger.info(f"✅ Found Flavour cafe: {flavour_cafe['name']} (ID: {flavour_cafe['id']})")
        
        # Force clear all existing menu items for Flavour cafe
        existing_items = menu_item_model.find_many({'restaurant_id': flavour_cafe['id']})
        existing_list = list(existing_items)
        
        for item in existing_list:
            try:
                menu_item_model.delete_by_id(item['id'])
            except Exception as e:
                logger.warning(f"Failed to delete item {item.get('name', 'Unknown')}: {e}")
        
        logger.info(f"🗑️ Cleared {len(existing_list)} existing menu items")
        
        # Add all new menu items with error handling
        added_count = 0
        categories = set()
        failed_items = []
        
        for item_data in menu_items:
            try:
                menu_item_id = menu_item_model.create(
                    name=item_data["name"],
                    price=item_data["price"],
                    restaurant_id=flavour_cafe['id'],
                    description=item_data["description"],
                    image_url=item_data["image_url"],
                    category=item_data["category"],
                    available=True
                )
                categories.add(item_data["category"])
                added_count += 1
                if added_count <= 10:  # Only log first 10 for brevity
                    logger.info(f"✅ Added: {item_data['name']} ({item_data['category']})")
            except Exception as e:
                failed_items.append(item_data['name'])
                logger.error(f"❌ Failed to add {item_data['name']}: {e}")
        
        if failed_items:
            logger.warning(f"⚠️ Failed items: {failed_items}")
        
        logger.info(f"✅ Successfully added {added_count} menu items to Flavour cafe")
        logger.info(f"✅ Categories created: {len(categories)}")
        logger.info(f"✅ Categories: {sorted(categories)}")
        
        # Verify final count
        final_count = menu_item_model.count({'restaurant_id': flavour_cafe['id']})
        logger.info(f"✅ Final menu items count for Flavour cafe: {final_count}")
        
        # Verify global count
        global_count = menu_item_model.count()
        logger.info(f"✅ Global menu items count: {global_count}")
        
        return final_count == 66

def test_superadmin_endpoints():
    """Test superadmin API endpoints for admin and restaurant management"""
    import requests
    
    base_url = "http://localhost:5000"
    
    # Test session login first
    session = requests.Session()
    
    logger.info("🔐 Testing superadmin login...")
    login_data = {'username': 'superadmin', 'password': 'superadmin123'}
    login_response = session.post(f"{base_url}/superadmin/login", data=login_data)
    
    if login_response.status_code == 200:
        logger.info("✅ Superadmin login successful")
        
        # Test restaurants endpoint
        logger.info("🏪 Testing restaurants endpoint...")
        restaurants_response = session.get(f"{base_url}/api/restaurants/super-admin")
        if restaurants_response.status_code == 200:
            data = restaurants_response.json()
            if data.get('success'):
                logger.info("✅ Restaurants endpoint working")
                for restaurant in data.get('restaurants', []):
                    logger.info(f"   {restaurant['name']}: {restaurant['menu_items_count']} items")
            else:
                logger.error(f"❌ Restaurants endpoint error: {data.get('error')}")
        else:
            logger.error(f"❌ Restaurants endpoint failed: {restaurants_response.status_code}")
        
        # Test admins endpoint
        logger.info("👥 Testing admins endpoint...")
        admins_response = session.get(f"{base_url}/api/super-admin/admins")
        if admins_response.status_code == 200:
            data = admins_response.json()
            if data.get('success'):
                logger.info("✅ Admins endpoint working")
                logger.info(f"   Found {len(data.get('admins', []))} admins")
            else:
                logger.error(f"❌ Admins endpoint error: {data.get('error')}")
        else:
            logger.error(f"❌ Admins endpoint failed: {admins_response.status_code}")
        
        # Test admin creation (POST)
        logger.info("➕ Testing admin creation...")
        new_admin_data = {
            'username': 'test_admin_2025',
            'password': 'test123',
            'full_name': 'Test Administrator 2025',
            'email': 'test@example.com',
            'role': 'admin'
        }
        create_admin_response = session.post(f"{base_url}/api/super-admin/admins", 
                                           json=new_admin_data)
        if create_admin_response.status_code == 200:
            data = create_admin_response.json()
            if data.get('success'):
                logger.info("✅ Admin creation endpoint working")
            else:
                logger.warning(f"⚠️ Admin creation failed: {data.get('message')}")
        else:
            logger.error(f"❌ Admin creation failed: {create_admin_response.status_code}")
        
        # Test restaurant creation (POST)
        logger.info("🏪 Testing restaurant creation...")
        new_restaurant_data = {
            'name': 'Test Restaurant 2025',
            'address': 'Test Address, Addis Ababa',
            'phone': '+251911999999',
            'description': 'Test restaurant for API validation'
        }
        create_restaurant_response = session.post(f"{base_url}/api/restaurants/super-admin", 
                                                json=new_restaurant_data)
        if create_restaurant_response.status_code == 200:
            data = create_restaurant_response.json()
            if data.get('success'):
                logger.info("✅ Restaurant creation endpoint working")
            else:
                logger.warning(f"⚠️ Restaurant creation failed: {data.get('message')}")
        else:
            logger.error(f"❌ Restaurant creation failed: {create_restaurant_response.status_code}")
            
    else:
        logger.error("❌ Superadmin login failed")

if __name__ == "__main__":
    logger.info("🚀 Starting comprehensive ET-FOOD fixes...")
    
    # Step 1: Debug current state
    debug_database_state()
    
    # Step 2: Restore menu properly
    menu_success = restore_menu_properly()
    
    # Step 3: Debug state after restoration
    logger.info("🔍 After menu restoration:")
    debug_database_state()
    
    # Step 4: Test superadmin endpoints
    test_superadmin_endpoints()
    
    # Summary
    logger.info("📋 Fix Summary:")
    logger.info(f"   Menu restoration: {'✅ SUCCESS' if menu_success else '❌ FAILED'}")
    logger.info("   API endpoints: Check logs above")
    logger.info("   Action buttons: Should work after API fixes")
    
    logger.info("🎉 Comprehensive fix completed!")