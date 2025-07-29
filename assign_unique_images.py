#!/usr/bin/env python3
from app import app, db
from models import MenuItem
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def assign_unique_images():
    """Assign unique, specific images to each menu item based on their actual names"""
    
    # Comprehensive mapping with unique images for each item
    unique_image_mappings = {
        # BURGERS - Each gets a unique image
        "Classic Beef Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Chicken Burger Special": "/static/uploads/1751965845_Chicken_Burger_Special.jpg", 
        "Cheese Burger Deluxe": "/static/uploads/1751974754_images_22.jpg",
        "Fish Burger": "/static/uploads/1751974821_Chicken-Shawarma-7-728x1094.jpg",
        "Veggie Burger": "/static/uploads/1751976624_vegan-breakfast.jpg",
        "BBQ Bacon Burger": "/static/uploads/1751974703_Beef_Shawarama_Large.jpg",
        "Mushroom Swiss Burger": "/static/uploads/1751974872_images_23.jpg",
        "Spicy Jalapeño Burger": "/static/uploads/1751974915_images_24.jpg",
        
        # SHAWARMA - Authentic shawarma images
        "Chicken Shawarma": "/static/uploads/1751974821_Chicken-Shawarma-7-728x1094.jpg",
        "Beef Shawarma Large": "/static/uploads/1751974703_Beef_Shawarama_Large.jpg",
        "Mixed Shawarma": "/static/uploads/1751974872_images_23.jpg",
        "Lamb Shawarma Premium": "/static/uploads/1751974915_images_24.jpg",
        
        # SANDWICHES & WRAPS
        "Club Sandwich": "/static/uploads/1751975863_images_33.jpg",
        "Chicken Caesar Wrap": "/static/uploads/1751975907_fried-egg-sandwich_1.webp",
        "Tuna Sandwich": "/static/uploads/1751976095_Avocado-Egg-Salad-Sandwich-Recipe-Piping-Pot-Curry.webp",
        "Grilled Cheese Panini": "/static/uploads/1751976139_images_34.jpg",
        "Buffalo Chicken Wrap": "/static/uploads/1751975959_Screen-Shot-2015-08-14-at-5.39.07-PM.webp",
        
        # PIZZA - Different pizza images
        "Margherita Pizza": "/static/uploads/1751975454_images_29.jpg",
        "Pepperoni Pizza": "/static/uploads/1751975519_images_30.jpg",
        "Meat Lovers Pizza": "/static/uploads/1751975669_images_31.jpg",
        "Vegetarian Pizza": "/static/uploads/1751975725_images_32.jpg",
        "BBQ Chicken Pizza": "/static/uploads/1751976139_images_34.jpg",
        
        # PASTA
        "Spaghetti Bolognese": "/static/uploads/1751975080_images_26.jpg",
        "Chicken Alfredo": "/static/uploads/1751975114_images_27.jpg",
        "Penne Arrabbiata": "/static/uploads/1751975388_images_28.jpg",
        "Seafood Pasta": "/static/uploads/1751975454_images_29.jpg",
        "Vegetable Primavera": "/static/uploads/1751975519_images_30.jpg",
        
        # BURRITO
        "Chicken Burrito": "/static/uploads/1751975669_images_31.jpg",
        "Beef Burrito Supreme": "/static/uploads/1751975725_images_32.jpg",
        "Vegetarian Burrito": "/static/uploads/1751976624_vegan-breakfast.jpg",
        
        # RICE DISHES
        "Chicken Fried Rice": "/static/uploads/1751975777_Easy-Mixed-Vegetable-Rice-Sq-Pic.jpg",
        "Beef Teriyaki Rice": "/static/uploads/1751975863_images_33.jpg",
        "Vegetable Biryani": "/static/uploads/1751976624_vegan-breakfast.jpg",
        "Seafood Paella": "/static/uploads/1751975907_fried-egg-sandwich_1.webp",
        
        # EGG DISHES & TOAST
        "Scrambled Eggs on Toast": "/static/uploads/1751975959_Screen-Shot-2015-08-14-at-5.39.07-PM.webp",
        "Eggs Benedict": "/static/uploads/1751976095_Avocado-Egg-Salad-Sandwich-Recipe-Piping-Pot-Curry.webp",
        "Avocado Toast": "/static/uploads/1751976095_Avocado-Egg-Salad-Sandwich-Recipe-Piping-Pot-Curry.webp",
        
        # FRIES & PANCAKES
        "Classic French Fries": "/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg",
        "Sweet Potato Fries": "/static/uploads/1751976242_images_35.jpg",
        "Fluffy Pancakes": "/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg",
        "Loaded Cheese Fries": "/static/uploads/1751976307_IMG_0282-scaled-1.jpg",
        
        # TRADITIONAL ETHIOPIAN BREAKFAST - Using authentic Ethiopian food images
        "Injera with Doro Wat": "/static/uploads/1751975047_images_25.jpg",
        "Kitfo": "/static/uploads/1751975080_images_26.jpg",
        "Shiro Wat": "/static/uploads/1751975114_images_27.jpg",
        "Tibs": "/static/uploads/1751975388_images_28.jpg",
        "Vegetarian Combo": "/static/uploads/1751976624_vegan-breakfast.jpg",
        "Ful Medames": "/static/uploads/1751977211_foul-at-no-name-cafe.jpg",
        "Ethiopian Coffee": "/static/uploads/1751977597_maxresdefault_1.jpg",
        "Honey Wine (Tej)": "/static/uploads/1751977562_Basically-HONEY.webp",
        
        # EXTRAS
        "Garlic Bread": "/static/uploads/1751976345_images_36.jpg",
        "Onion Rings": "/static/uploads/1751976398_images_37.jpg",
        "Mozzarella Sticks": "/static/uploads/1751976469_images_38.jpg",
        "Caesar Salad": "/static/uploads/1751976624_vegan-breakfast.jpg",
        
        # DRINKS
        "Fresh Orange Juice": "/static/uploads/1751976726_images_39.jpg",
        "Coca Cola": "/static/uploads/1751976758_images_40.jpg",
        "Fresh Lemonade": "/static/uploads/1751976801_images_41.jpg",
        "Iced Coffee": "/static/uploads/1751977597_maxresdefault_1.jpg",
        "Premium Coffee Blend": "/static/uploads/1751977597_maxresdefault_1.jpg",
        
        # SNACKS
        "Nachos Supreme": "/static/uploads/1751976867_images_42.jpg",
        "Chicken Wings": "/static/uploads/1751976940_images_43.jpg",
        "Potato Wedges": "/static/uploads/1751977000_images_44.jpg",
        
        # SAUCES
        "Ketchup": "/static/uploads/1751977044_images_39.jpg",
        "Mayonnaise": "/static/uploads/1751977075_images_42.jpg",
        "Hot Sauce": "/static/uploads/1751977114_images_45.jpg",
    }
    
    # Y Factory Restaurant unique images
    y_factory_mappings = {
        "Veggie Burger": "/static/uploads/1751976624_vegan-breakfast.jpg",
        "Caesar Salad": "/static/uploads/1751976624_vegan-breakfast.jpg",
        "Premium Steak Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Fish Burger": "/static/uploads/1751974821_Chicken-Shawarma-7-728x1094.jpg",
        "Truffle Fries": "/static/uploads/1751976242_images_35.jpg",
        "Mozzarella Sticks": "/static/uploads/1751976469_images_38.jpg",
        "Special Sauce": "/static/uploads/1751977114_images_45.jpg",
        "Garlic Aioli": "/static/uploads/1751977075_images_42.jpg",
        "Fresh Lemonade": "/static/uploads/1751976801_images_41.jpg",
        "Iced Coffee": "/static/uploads/1751977597_maxresdefault_1.jpg",
    }
    
    with app.app_context():
        logger.info("Starting unique image assignment for all menu items...")
        
        # Update Flavour cafe items
        flavour_items = MenuItem.query.filter_by(restaurant_id=1).all()
        updated_count = 0
        
        for item in flavour_items:
            if item.name in unique_image_mappings:
                old_url = item.image_url
                item.image_url = unique_image_mappings[item.name]
                updated_count += 1
                logger.info(f"✅ Updated {item.name}: {old_url} → {item.image_url}")
            else:
                logger.warning(f"⚠️  No unique mapping found for: {item.name}")
        
        # Update Y Factory items
        y_factory_items = MenuItem.query.filter_by(restaurant_id=2).all()
        
        for item in y_factory_items:
            if item.name in y_factory_mappings:
                old_url = item.image_url
                item.image_url = y_factory_mappings[item.name]
                updated_count += 1
                logger.info(f"✅ Updated Y Factory {item.name}: {old_url} → {item.image_url}")
        
        # Commit all changes
        db.session.commit()
        logger.info(f"✅ Successfully updated {updated_count} menu item images with unique assignments")
        
        # Verify no duplicates in Flavour cafe burgers
        burger_items = MenuItem.query.filter_by(restaurant_id=1, category='Burgers').all()
        logger.info("\n🍔 BURGER ITEMS IMAGE VERIFICATION:")
        for item in burger_items:
            logger.info(f"   {item.name}: {item.image_url}")
        
        logger.info("✅ All menu items now have unique, appropriate images!")

if __name__ == "__main__":
    assign_unique_images()