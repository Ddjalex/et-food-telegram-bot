#!/usr/bin/env python3
"""
Restore real food images for all menu items
This script updates the database to use actual uploaded food images instead of placeholders
"""

import os
from app import app
from app import db
from models import MenuItem

# Mapping of food items to their actual uploaded images
FOOD_IMAGE_MAPPING = {
    'Classic Burger': '1751892160_22.JPG',
    'Chicken Burger': '1751892507_languge_2.jpg', 
    'Beef Shawarma': '1751974703_Beef_Shawarama_Large.jpg',
    'Mixed Platter': '1751965845_Chicken_Burger_Special.jpg',
    'French Fries': '1751898445_st3.jpg',
    'Coca Cola': '1751974754_images_22.jpg',
    'Chicken Shawarma': '1751974821_Chicken-Shawarma-7-728x1094.jpg',
    'Vegetable Sandwich': '1751974872_images_23.jpg',
    'Beef Sandwich': '1751974915_images_24.jpg', 
    'Club Sandwich': '1751975047_images_25.jpg',
    'Tuna Sandwich': '1751975080_images_26.jpg',
    'Grilled Chicken': '1751975114_images_27.jpg',
    'Fish Fillet': '1751975388_images_28.jpg',
    'Pasta Bolognese': '1751975454_images_29.jpg',
    'Carbonara': '1751975519_images_30.jpg',
    'Margherita Pizza': '1751975669_images_31.jpg',
    'Pepperoni Pizza': '1751975728_images_32.jpg',
    'Chicken Pizza': '1751975792_images_33.jpg',
    'Vegetable Pizza': '1751975851_images_34.jpg',
    'Ethiopian Coffee': '1751975915_images_35.jpg',
    'Fresh Juice': '1751975979_images_36.jpg',
    'Smoothie': '1751976043_images_37.jpg',
    'Ice Cream': '1751976107_images_38.jpg',
    'Cake': '1751976171_images_39.jpg',
    'Traditional Injera': '1751976235_images_40.jpg'
}

def restore_food_images():
    """Update all menu items with real food images"""
    
    with app.app_context():
        print("🍽️ Restoring real food images...")
        
        # Get all menu items
        menu_items = MenuItem.query.all()
        print(f"📋 Found {len(menu_items)} menu items")
        
        updated_count = 0
        
        for item in menu_items:
            # Check if we have a real image for this item
            if item.name in FOOD_IMAGE_MAPPING:
                image_filename = FOOD_IMAGE_MAPPING[item.name]
                new_image_url = f'/static/uploads/{image_filename}'
                
                # Check if the image file actually exists
                image_path = os.path.join('static/uploads', image_filename)
                if os.path.exists(image_path):
                    # Update the database
                    item.image_url = new_image_url
                    updated_count += 1
                    print(f"✅ Updated {item.name} -> {image_filename}")
                else:
                    print(f"⚠️  Image not found: {image_path}")
            else:
                # Try to find a generic food image for items without specific mapping
                available_images = [
                    '1751898649_photo_2025-07-07_14-35-57.jpg',
                    '1751898931_lunguge1.jpg', 
                    '1751901884_lunguge1.jpg'
                ]
                
                # Use a generic food image based on category
                if item.category == 'burgers':
                    generic_image = '1751892160_22.JPG'
                elif item.category == 'drinks':
                    generic_image = '1751974754_images_22.jpg'
                elif item.category == 'snacks':
                    generic_image = '1751898445_st3.jpg'
                else:
                    generic_image = available_images[0]
                
                new_image_url = f'/static/uploads/{generic_image}'
                image_path = os.path.join('static/uploads', generic_image)
                
                if os.path.exists(image_path):
                    item.image_url = new_image_url
                    updated_count += 1
                    print(f"📷 Generic image for {item.name} -> {generic_image}")
        
        # Commit all changes
        db.session.commit()
        print(f"💾 Successfully updated {updated_count} menu items with real food images")
        
        # Show final status
        placeholder_count = MenuItem.query.filter(MenuItem.image_url.contains('placeholder')).count()
        real_image_count = MenuItem.query.filter(MenuItem.image_url.contains('/static/uploads/')).count()
        
        print(f"📊 Final status:")
        print(f"   Real food images: {real_image_count}")
        print(f"   Placeholder images: {placeholder_count}")
        print(f"   Total items: {real_image_count + placeholder_count}")
        
        return updated_count

if __name__ == '__main__':
    restore_food_images()