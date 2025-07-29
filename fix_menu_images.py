#!/usr/bin/env python3
from app import app, db
from models import MenuItem
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_all_menu_images():
    """Update all menu items with correct image URLs from uploaded files"""
    
    # Mapping of menu items to actual uploaded images
    image_mappings = {
        # Burgers
        "Chicken Burger Special": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Classic Beef Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Cheese Burger Deluxe": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Fish Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Veggie Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "BBQ Bacon Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Mushroom Swiss Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        "Spicy Jalapeño Burger": "/static/uploads/1751965845_Chicken_Burger_Special.jpg",
        
        # Shawarma
        "Chicken Shawarma": "/static/uploads/1751974821_Chicken-Shawarma-7-728x1094.jpg",
        "Beef Shawarma Large": "/static/uploads/1751974703_Beef_Shawarama_Large.jpg",
        "Mixed Shawarma": "/static/uploads/1751974821_Chicken-Shawarma-7-728x1094.jpg",
        "Lamb Shawarma Premium": "/static/uploads/1751974703_Beef_Shawarama_Large.jpg",
        
        # Traditional Ethiopian Breakfast
        "Injera with Doro Wat": "/static/uploads/1751975047_images_25.jpg",
        "Kitfo": "/static/uploads/1751975080_images_26.jpg",
        "Shiro Wat": "/static/uploads/1751975114_images_27.jpg",
        "Tibs": "/static/uploads/1751975388_images_28.jpg",
        "Vegetarian Combo": "/static/uploads/1751976624_vegan-breakfast.jpg",
        "Ful Medames": "/static/uploads/1751977211_foul-at-no-name-cafe.jpg",
        "Ethiopian Coffee": "/static/uploads/1751977597_maxresdefault_1.jpg",
        "Honey Wine (Tej)": "/static/uploads/1751977562_Basically-HONEY.webp",
        
        # Rice Dishes
        "Chicken Fried Rice": "/static/uploads/1751975777_Easy-Mixed-Vegetable-Rice-Sq-Pic.jpg",
        "Beef Teriyaki Rice": "/static/uploads/1751975777_Easy-Mixed-Vegetable-Rice-Sq-Pic.jpg",
        "Vegetable Biryani": "/static/uploads/1751975777_Easy-Mixed-Vegetable-Rice-Sq-Pic.jpg",
        "Seafood Paella": "/static/uploads/1751975777_Easy-Mixed-Vegetable-Rice-Sq-Pic.jpg",
        
        # Egg Dishes & Toast
        "Scrambled Eggs on Toast": "/static/uploads/1751975959_Screen-Shot-2015-08-14-at-5.39.07-PM.webp",
        "Eggs Benedict": "/static/uploads/1751975959_Screen-Shot-2015-08-14-at-5.39.07-PM.webp",
        "Avocado Toast": "/static/uploads/1751976095_Avocado-Egg-Salad-Sandwich-Recipe-Piping-Pot-Curry.webp",
        
        # Fries & Pancakes
        "Classic French Fries": "/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg",
        "Sweet Potato Fries": "/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg",
        "Fluffy Pancakes": "/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg",
        "Loaded Cheese Fries": "/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg",
        
        # Sandwiches & Wraps
        "Club Sandwich": "/static/uploads/1751975863_images_33.jpg",
        "Chicken Caesar Wrap": "/static/uploads/1751975863_images_33.jpg",
        "Tuna Sandwich": "/static/uploads/1751975863_images_33.jpg",
        "Grilled Cheese Panini": "/static/uploads/1751975863_images_33.jpg",
        "Buffalo Chicken Wrap": "/static/uploads/1751975863_images_33.jpg",
        
        # General fallback for remaining items
        "default": "/static/uploads/1751974754_images_22.jpg"
    }
    
    with app.app_context():
        logger.info("Starting image URL updates for all menu items...")
        
        # Get all menu items
        menu_items = MenuItem.query.filter_by(restaurant_id=1).all()
        
        updated_count = 0
        for item in menu_items:
            # Check if we have a specific mapping for this item
            if item.name in image_mappings:
                new_image_url = image_mappings[item.name]
            else:
                # Use default image for items not specifically mapped
                new_image_url = image_mappings["default"]
            
            # Update the image URL
            item.image_url = new_image_url
            updated_count += 1
            logger.info(f"Updated {item.name}: {new_image_url}")
        
        # Update Y Factory Restaurant items with different images
        y_factory_items = MenuItem.query.filter_by(restaurant_id=2).all()
        for item in y_factory_items:
            item.image_url = "/static/uploads/1751974915_images_24.jpg"
            updated_count += 1
            logger.info(f"Updated Y Factory item {item.name}")
        
        # Commit all changes
        db.session.commit()
        logger.info(f"✅ Successfully updated {updated_count} menu item images")
        
        # Verify the updates
        flavour_items = MenuItem.query.filter_by(restaurant_id=1).count()
        y_factory_items_count = MenuItem.query.filter_by(restaurant_id=2).count()
        
        logger.info(f"✅ Flavour cafe items: {flavour_items}")
        logger.info(f"✅ Y Factory items: {y_factory_items_count}")
        logger.info("✅ All images now point to actual uploaded files")

if __name__ == "__main__":
    fix_all_menu_images()