#!/usr/bin/env python3
from app import app, db
from models import MenuItem
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def restore_flavour_cafe_menu():
    """Restore complete Flavour cafe menu with 64 food products"""
    
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
        {"name": "Shiro Wat", "price": 150.0, "description": "Ground chickpea stew", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/shiro_wat.jpg"},
        {"name": "Tibs", "price": 220.0, "description": "Sautéed meat with vegetables", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/tibs.jpg"},
        {"name": "Vegetarian Combo", "price": 180.0, "description": "Mixed vegetarian dishes on injera", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/veggie_combo.jpg"},
        {"name": "Ful Medames", "price": 120.0, "description": "Fava beans with Ethiopian spices", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/ful.jpg"},
        {"name": "Ethiopian Coffee", "price": 60.0, "description": "Traditional coffee ceremony", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/ethiopian_coffee.jpg"},
        {"name": "Honey Wine (Tej)", "price": 150.0, "description": "Traditional Ethiopian honey wine", "category": "Traditional Ethiopian Breakfast", "image_url": "/static/uploads/tej.jpg"},
        
        # Extras (4 items)
        {"name": "Garlic Bread", "price": 60.0, "description": "Toasted bread with garlic butter", "category": "Extras", "image_url": "/static/uploads/garlic_bread.jpg"},
        {"name": "Onion Rings", "price": 90.0, "description": "Crispy beer-battered onion rings", "category": "Extras", "image_url": "/static/uploads/onion_rings.jpg"},
        {"name": "Mozzarella Sticks", "price": 120.0, "description": "Breaded mozzarella with marinara", "category": "Extras", "image_url": "/static/uploads/mozzarella_sticks.jpg"},
        {"name": "Caesar Salad", "price": 140.0, "description": "Crisp romaine with Caesar dressing", "category": "Extras", "image_url": "/static/uploads/caesar_salad.jpg"},
        
        # Drinks (4 items)
        {"name": "Fresh Orange Juice", "price": 80.0, "description": "Freshly squeezed orange juice", "category": "Drinks", "image_url": "/static/uploads/orange_juice.jpg"},
        {"name": "Coca Cola", "price": 50.0, "description": "Classic Coca Cola", "category": "Drinks", "image_url": "/static/uploads/coca_cola.jpg"},
        {"name": "Fresh Lemonade", "price": 70.0, "description": "Homemade lemonade with mint", "category": "Drinks", "image_url": "/static/uploads/lemonade.jpg"},
        {"name": "Iced Coffee", "price": 90.0, "description": "Cold brew coffee with milk", "category": "Drinks", "image_url": "/static/uploads/iced_coffee.jpg"},
        
        # Snacks (3 items)
        {"name": "Nachos Supreme", "price": 160.0, "description": "Tortilla chips with cheese and jalapeños", "category": "Snacks", "image_url": "/static/uploads/nachos.jpg"},
        {"name": "Chicken Wings", "price": 180.0, "description": "Spicy buffalo wings with blue cheese", "category": "Snacks", "image_url": "/static/uploads/wings.jpg"},
        {"name": "Potato Wedges", "price": 100.0, "description": "Seasoned potato wedges with sour cream", "category": "Snacks", "image_url": "/static/uploads/wedges.jpg"},
        
        # Sauces (3 items)
        {"name": "Ketchup", "price": 15.0, "description": "Classic tomato ketchup", "category": "Sauces", "image_url": "/static/uploads/ketchup.jpg"},
        {"name": "Mayonnaise", "price": 15.0, "description": "Creamy mayonnaise", "category": "Sauces", "image_url": "/static/uploads/mayo.jpg"},
        {"name": "Hot Sauce", "price": 20.0, "description": "Spicy chili sauce", "category": "Sauces", "image_url": "/static/uploads/hot_sauce.jpg"},
    ]
    
    with app.app_context():
        logger.info("Starting complete menu restoration for Flavour cafe...")
        
        # Add all menu items
        for item_data in menu_items:
            menu_item = MenuItem(
                name=item_data["name"],
                price=item_data["price"],
                description=item_data["description"],
                image_url=item_data["image_url"],
                category=item_data["category"],
                available=True,
                restaurant_id=1  # Flavour cafe
            )
            db.session.add(menu_item)
        
        db.session.commit()
        logger.info(f"✅ Successfully added {len(menu_items)} menu items to Flavour cafe")
        
        # Verify counts
        total_items = MenuItem.query.filter_by(restaurant_id=1).count()
        logger.info(f"✅ Total menu items for Flavour cafe: {total_items}")
        
        # Count by category
        from sqlalchemy import func
        category_counts = db.session.query(
            MenuItem.category,
            func.count(MenuItem.id)
        ).filter_by(restaurant_id=1).group_by(MenuItem.category).all()
        
        for category, count in category_counts:
            logger.info(f"   {category}: {count} items")

if __name__ == "__main__":
    restore_flavour_cafe_menu()