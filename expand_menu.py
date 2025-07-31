#!/usr/bin/env python3
"""
Expand menu to 64 food products across 14 categories for Flavour cafe
"""
from app import app, db
from models import MenuItem, Restaurant, Category

def expand_menu():
    """Expand menu to 64 items across 14 categories"""
    with app.app_context():
        # Get Flavour cafe
        flavour_cafe = Restaurant.query.filter_by(name='Flavour cafe | E.Fabrica').first()
        if not flavour_cafe:
            print("Flavour cafe not found")
            return
        
        # Clear existing menu items and categories
        MenuItem.query.filter_by(restaurant_id=flavour_cafe.id).delete()
        Category.query.filter_by(restaurant_id=flavour_cafe.id).delete()
        db.session.commit()
        
        # Define 14 categories
        categories_data = [
            {'name': 'Ethiopian Traditional', 'description': 'Authentic Ethiopian dishes', 'icon': '🇪🇹'},
            {'name': 'Burgers & Sandwiches', 'description': 'Delicious burgers and sandwiches', 'icon': '🍔'},
            {'name': 'Pizza', 'description': 'Wood-fired pizzas', 'icon': '🍕'},
            {'name': 'Pasta & Italian', 'description': 'Italian pasta and dishes', 'icon': '🍝'},
            {'name': 'Grilled & BBQ', 'description': 'Grilled meats and BBQ', 'icon': '🔥'},
            {'name': 'Seafood', 'description': 'Fresh seafood dishes', 'icon': '🐟'},
            {'name': 'Vegetarian & Vegan', 'description': 'Plant-based options', 'icon': '🥗'},
            {'name': 'Rice & Biryani', 'description': 'Rice dishes and biryani', 'icon': '🍚'},
            {'name': 'Soups & Stews', 'description': 'Hearty soups and stews', 'icon': '🍲'},
            {'name': 'Breakfast & Brunch', 'description': 'Morning meals', 'icon': '🥞'},
            {'name': 'Desserts', 'description': 'Sweet treats', 'icon': '🍰'},
            {'name': 'Beverages', 'description': 'Hot and cold drinks', 'icon': '☕'},
            {'name': 'Snacks & Appetizers', 'description': 'Light bites', 'icon': '🥨'},
            {'name': 'Healthy Options', 'description': 'Nutritious choices', 'icon': '💚'}
        ]
        
        # Create categories
        for cat_data in categories_data:
            category = Category(
                name=cat_data['name'],
                description=cat_data['description'],
                icon=cat_data['icon'],
                restaurant_id=flavour_cafe.id
            )
            db.session.add(category)
        
        # Define 64 menu items across categories
        menu_items = [
            # Ethiopian Traditional (8 items)
            {'name': 'Injera with Doro Wat', 'price': 180.0, 'description': 'Traditional Ethiopian sourdough flatbread with spicy chicken stew', 'category': 'ethiopian', 'image_url': '/static/uploads/1751975047_images_25.jpg'},
            {'name': 'Kitfo', 'price': 200.0, 'description': 'Ethiopian steak tartare with mitmita and cottage cheese', 'category': 'ethiopian', 'image_url': '/static/uploads/1751975080_images_26.jpg'},
            {'name': 'Tibs', 'price': 160.0, 'description': 'Sautéed beef with onions and Ethiopian spices', 'category': 'ethiopian', 'image_url': '/static/uploads/1751975388_images_28.jpg'},
            {'name': 'Shiro Wat', 'price': 120.0, 'description': 'Traditional chickpea flour stew with berbere', 'category': 'ethiopian', 'image_url': '/static/uploads/1751975114_images_27.jpg'},
            {'name': 'Gomen Wat', 'price': 100.0, 'description': 'Spiced collard greens with garlic and ginger', 'category': 'ethiopian', 'image_url': '/static/uploads/1751976624_vegan-breakfast.jpg'},
            {'name': 'Misir Wat', 'price': 110.0, 'description': 'Red lentil stew with berbere spice', 'category': 'ethiopian', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Vegetarian Combo', 'price': 140.0, 'description': 'Assorted vegetarian dishes on injera', 'category': 'ethiopian', 'image_url': '/static/uploads/1751976624_vegan-breakfast.jpg'},
            {'name': 'Ethiopian Coffee Ceremony', 'price': 60.0, 'description': 'Traditional coffee ceremony with popcorn', 'category': 'ethiopian', 'image_url': '/static/placeholder-food.jpg'},
            
            # Burgers & Sandwiches (6 items)
            {'name': 'Classic Beef Burger', 'price': 150.0, 'description': 'Juicy beef patty with lettuce, tomato, and special sauce', 'category': 'burgers', 'image_url': '/static/uploads/1751975959_Screen-Shot-2015-08-14-at-5.39.07-PM.webp'},
            {'name': 'Chicken Shawarma', 'price': 130.0, 'description': 'Tender chicken shawarma with tahini sauce', 'category': 'burgers', 'image_url': '/static/uploads/1751976242_images_35.jpg'},
            {'name': 'Double Cheeseburger', 'price': 180.0, 'description': 'Two beef patties with double cheese', 'category': 'burgers', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Chicken Burger', 'price': 140.0, 'description': 'Grilled chicken breast with avocado', 'category': 'burgers', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Fish Sandwich', 'price': 160.0, 'description': 'Crispy fish fillet with tartar sauce', 'category': 'burgers', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Veggie Burger', 'price': 120.0, 'description': 'Plant-based patty with fresh vegetables', 'category': 'burgers', 'image_url': '/static/placeholder-food.jpg'},
            
            # Pizza (5 items)
            {'name': 'Margherita Pizza', 'price': 170.0, 'description': 'Fresh mozzarella, tomato sauce, and basil', 'category': 'pizza', 'image_url': '/static/uploads/1751976307_IMG_0282-scaled-1.jpg'},
            {'name': 'Pepperoni Pizza', 'price': 190.0, 'description': 'Classic pepperoni with mozzarella cheese', 'category': 'pizza', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Vegetarian Pizza', 'price': 180.0, 'description': 'Bell peppers, onions, mushrooms, and olives', 'category': 'pizza', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Meat Lovers Pizza', 'price': 220.0, 'description': 'Pepperoni, sausage, ham, and bacon', 'category': 'pizza', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Hawaiian Pizza', 'price': 185.0, 'description': 'Ham and pineapple with cheese', 'category': 'pizza', 'image_url': '/static/placeholder-food.jpg'},
            
            # Pasta & Italian (5 items)
            {'name': 'Pasta Carbonara', 'price': 140.0, 'description': 'Creamy pasta with bacon and parmesan', 'category': 'pasta', 'image_url': '/static/uploads/1751975863_images_33.jpg'},
            {'name': 'Spaghetti Bolognese', 'price': 135.0, 'description': 'Classic meat sauce with spaghetti', 'category': 'pasta', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Fettuccine Alfredo', 'price': 130.0, 'description': 'Creamy white sauce with fettuccine', 'category': 'pasta', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Penne Arrabbiata', 'price': 125.0, 'description': 'Spicy tomato sauce with penne pasta', 'category': 'pasta', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Lasagna', 'price': 160.0, 'description': 'Layered pasta with meat and cheese', 'category': 'pasta', 'image_url': '/static/placeholder-food.jpg'},
            
            # Grilled & BBQ (5 items)
            {'name': 'Grilled Chicken Breast', 'price': 180.0, 'description': 'Tender grilled chicken with herbs', 'category': 'grilled', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'BBQ Ribs', 'price': 220.0, 'description': 'Slow-cooked ribs with BBQ sauce', 'category': 'grilled', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Grilled Steak', 'price': 250.0, 'description': 'Premium beef steak grilled to perfection', 'category': 'grilled', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Grilled Fish', 'price': 200.0, 'description': 'Fresh fish grilled with lemon', 'category': 'grilled', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Mixed Grill Platter', 'price': 280.0, 'description': 'Assorted grilled meats and vegetables', 'category': 'grilled', 'image_url': '/static/placeholder-food.jpg'},
            
            # Seafood (4 items)
            {'name': 'Grilled Salmon', 'price': 230.0, 'description': 'Atlantic salmon with herbs', 'category': 'seafood', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Shrimp Scampi', 'price': 210.0, 'description': 'Garlic butter shrimp with pasta', 'category': 'seafood', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Fish and Chips', 'price': 160.0, 'description': 'Crispy battered fish with fries', 'category': 'seafood', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Seafood Platter', 'price': 280.0, 'description': 'Mixed seafood with rice', 'category': 'seafood', 'image_url': '/static/placeholder-food.jpg'},
            
            # Vegetarian & Vegan (4 items)
            {'name': 'Quinoa Buddha Bowl', 'price': 140.0, 'description': 'Quinoa with roasted vegetables', 'category': 'vegetarian', 'image_url': '/static/uploads/1751976624_vegan-breakfast.jpg'},
            {'name': 'Avocado Toast', 'price': 90.0, 'description': 'Smashed avocado on sourdough', 'category': 'vegetarian', 'image_url': '/static/uploads/1751976095_Avocado-Egg-Salad-Sandwich-Recipe-Piping-Pot-Curry.webp'},
            {'name': 'Veggie Wrap', 'price': 110.0, 'description': 'Fresh vegetables in tortilla wrap', 'category': 'vegetarian', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Mediterranean Salad', 'price': 120.0, 'description': 'Mixed greens with feta and olives', 'category': 'vegetarian', 'image_url': '/static/placeholder-food.jpg'},
            
            # Rice & Biryani (4 items)
            {'name': 'Chicken Biryani', 'price': 170.0, 'description': 'Fragrant basmati rice with spiced chicken', 'category': 'rice', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Vegetable Biryani', 'price': 150.0, 'description': 'Mixed vegetables with basmati rice', 'category': 'rice', 'image_url': '/static/uploads/1751976624_vegan-breakfast.jpg'},
            {'name': 'Beef Teriyaki Rice', 'price': 160.0, 'description': 'Teriyaki beef over steamed rice', 'category': 'rice', 'image_url': '/static/uploads/1751975863_images_33.jpg'},
            {'name': 'Fried Rice', 'price': 120.0, 'description': 'Wok-fried rice with vegetables', 'category': 'rice', 'image_url': '/static/placeholder-food.jpg'},
            
            # Soups & Stews (3 items)
            {'name': 'Chicken Soup', 'price': 80.0, 'description': 'Homemade chicken soup with vegetables', 'category': 'soups', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Beef Stew', 'price': 140.0, 'description': 'Hearty beef stew with potatoes', 'category': 'soups', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Lentil Soup', 'price': 70.0, 'description': 'Nutritious red lentil soup', 'category': 'soups', 'image_url': '/static/placeholder-food.jpg'},
            
            # Breakfast & Brunch (4 items)
            {'name': 'Full English Breakfast', 'price': 150.0, 'description': 'Eggs, bacon, sausage, beans, and toast', 'category': 'breakfast', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Pancakes', 'price': 100.0, 'description': 'Fluffy pancakes with syrup', 'category': 'breakfast', 'image_url': '/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg'},
            {'name': 'Scrambled Eggs on Toast', 'price': 80.0, 'description': 'Creamy scrambled eggs on toast', 'category': 'breakfast', 'image_url': '/static/uploads/1751975959_Screen-Shot-2015-08-14-at-5.39.07-PM.webp'},
            {'name': 'Eggs Benedict', 'price': 130.0, 'description': 'Poached eggs with hollandaise sauce', 'category': 'breakfast', 'image_url': '/static/uploads/1751976095_Avocado-Egg-Salad-Sandwich-Recipe-Piping-Pot-Curry.webp'},
            
            # Desserts (3 items)
            {'name': 'Chocolate Cake', 'price': 80.0, 'description': 'Rich chocolate layer cake', 'category': 'desserts', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Tiramisu', 'price': 90.0, 'description': 'Classic Italian coffee dessert', 'category': 'desserts', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Ice Cream Sundae', 'price': 60.0, 'description': 'Vanilla ice cream with toppings', 'category': 'desserts', 'image_url': '/static/placeholder-food.jpg'},
            
            # Beverages (4 items)
            {'name': 'Ethiopian Coffee', 'price': 40.0, 'description': 'Traditional Ethiopian coffee ceremony style', 'category': 'beverages', 'image_url': '/static/uploads/1751976624_vegan-breakfast.jpg'},
            {'name': 'Fresh Orange Juice', 'price': 35.0, 'description': 'Freshly squeezed orange juice', 'category': 'beverages', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Iced Tea', 'price': 30.0, 'description': 'Refreshing iced tea with lemon', 'category': 'beverages', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Smoothie Bowl', 'price': 70.0, 'description': 'Mixed fruit smoothie with granola', 'category': 'beverages', 'image_url': '/static/placeholder-food.jpg'},
            
            # Snacks & Appetizers (4 items)
            {'name': 'French Fries', 'price': 50.0, 'description': 'Crispy golden French fries', 'category': 'snacks', 'image_url': '/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg'},
            {'name': 'Loaded Cheese Fries', 'price': 80.0, 'description': 'Fries topped with cheese and bacon', 'category': 'snacks', 'image_url': '/static/uploads/1751976307_IMG_0282-scaled-1.jpg'},
            {'name': 'Chicken Wings', 'price': 120.0, 'description': 'Spicy buffalo chicken wings', 'category': 'snacks', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Mozzarella Sticks', 'price': 90.0, 'description': 'Crispy mozzarella with marinara sauce', 'category': 'snacks', 'image_url': '/static/placeholder-food.jpg'},
            
            # Healthy Options (5 items)
            {'name': 'Grilled Chicken Salad', 'price': 140.0, 'description': 'Mixed greens with grilled chicken', 'category': 'healthy', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Quinoa Salad', 'price': 120.0, 'description': 'Protein-rich quinoa with vegetables', 'category': 'healthy', 'image_url': '/static/uploads/1751976624_vegan-breakfast.jpg'},
            {'name': 'Protein Bowl', 'price': 160.0, 'description': 'Lean protein with brown rice and vegetables', 'category': 'healthy', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Acai Bowl', 'price': 90.0, 'description': 'Antioxidant-rich acai with fresh fruits', 'category': 'healthy', 'image_url': '/static/placeholder-food.jpg'},
            {'name': 'Green Smoothie', 'price': 60.0, 'description': 'Kale, spinach, and fruit smoothie', 'category': 'healthy', 'image_url': '/static/placeholder-food.jpg'}
        ]
        
        # Add all menu items
        for item_data in menu_items:
            menu_item = MenuItem(
                name=item_data['name'],
                price=item_data['price'],
                description=item_data['description'],
                category=item_data['category'],
                image_url=item_data['image_url'],
                restaurant_id=flavour_cafe.id,
                available=True
            )
            db.session.add(menu_item)
        
        db.session.commit()
        print(f"✅ Expanded menu successfully!")
        print(f"   - Created {len(categories_data)} categories")
        print(f"   - Created {len(menu_items)} menu items")
        print(f"   - Total items for Flavour cafe: {MenuItem.query.filter_by(restaurant_id=flavour_cafe.id).count()}")

if __name__ == '__main__':
    expand_menu()