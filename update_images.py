#!/usr/bin/env python3
"""
Script to update all menu item images with high-quality food images
"""

from app import app, db
from models import MenuItem

# Image mappings with high-quality sources - using exact names from database
image_mappings = {
    # Burgers
    'Beef Burger Normal': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&h=300&fit=crop&auto=format',
    'Beef Burger Special': 'https://images.unsplash.com/photo-1594212699903-ec8a3eca50f5?w=400&h=300&fit=crop&auto=format',
    'Chicken Burger Normal': 'https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=400&h=300&fit=crop&auto=format',
    'Chicken Burger Special': 'https://images.unsplash.com/photo-1525059696034-4967a729002e?w=400&h=300&fit=crop&auto=format',
    
    # Shawarma
    'Beef Shawarama Large': 'https://images.unsplash.com/photo-1610057099443-fde8c4d50fbf?w=400&h=300&fit=crop&auto=format',
    'Beef Shawarama Small': 'https://images.unsplash.com/photo-1626028466266-d2dd6b23b0b5?w=400&h=300&fit=crop&auto=format',
    'Chicken Shawarama Large': 'https://images.unsplash.com/photo-1585238341710-4d3838a2c903?w=400&h=300&fit=crop&auto=format',
    'Chicken Shawarama Small': 'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400&h=300&fit=crop&auto=format',
    
    # Sandwiches & Wraps
    'Chicken Wrap': 'https://images.unsplash.com/photo-1567234669003-dce7a7a88821?w=400&h=300&fit=crop&auto=format',
    'Club Sandwich': 'https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=400&h=300&fit=crop&auto=format',
    'Egg Sandwich': 'https://images.unsplash.com/photo-1551326844-4df70f78d0e9?w=400&h=300&fit=crop&auto=format',
    'Tunna Sandwich': 'https://images.unsplash.com/photo-1626765515755-5839c1e2b29e?w=400&h=300&fit=crop&auto=format',
    'Tunna Wrap': 'https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=400&h=300&fit=crop&auto=format',
    'Vegetable Wrap': 'https://images.unsplash.com/photo-1574894709920-11b28e7367e3?w=400&h=300&fit=crop&auto=format',
    'Ahu Wrap': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop&auto=format',
    
    # Pizza
    'Chicken Pizza': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&h=300&fit=crop&auto=format',
    'Special Pizza': 'https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=400&h=300&fit=crop&auto=format',
    'Vegetable Pizza': 'https://images.unsplash.com/photo-1604382354936-07c5d9983bd3?w=400&h=300&fit=crop&auto=format',
    
    # Pasta
    'Pasta With Chicken': 'https://images.unsplash.com/photo-1611270629569-8b357cb88da9?w=400&h=300&fit=crop&auto=format',
    'Pasta With Tomato': 'https://images.unsplash.com/photo-1621996346565-e3dbc353d2e5?w=400&h=300&fit=crop&auto=format',
    'Pasta With Tunna': 'https://images.unsplash.com/photo-1595295333158-4742f28ceecb?w=400&h=300&fit=crop&auto=format',
    'Pasta With Vegetable': 'https://images.unsplash.com/photo-1555949258-eb67b1ef0ceb?w=400&h=300&fit=crop&auto=format',
    
    # Borrito
    'Borrito': 'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=400&h=300&fit=crop&auto=format',
    'Borrito Fasting': 'https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=400&h=300&fit=crop&auto=format',
    
    # Rice Dishes
    'Rice with Chicken': 'https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=400&h=300&fit=crop&auto=format',
    'Rice with Tomato': 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=400&h=300&fit=crop&auto=format',
    'Rice with Tunna': 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=400&h=300&fit=crop&auto=format',
    'Rice with Vegetable': 'https://images.unsplash.com/photo-1567234669003-dce7a7a88821?w=400&h=300&fit=crop&auto=format',
    
    # Egg Dishes & Toast
    'Egg Crumble': 'https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=400&h=300&fit=crop&auto=format',
    'Egg Sandwich': 'https://images.unsplash.com/photo-1551326844-4df70f78d0e9?w=400&h=300&fit=crop&auto=format',
    'Egg Silse': 'https://images.unsplash.com/photo-1608039829572-78524f79c4c7?w=400&h=300&fit=crop&auto=format',
    'Egg With Avocado': 'https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=400&h=300&fit=crop&auto=format',
    'Omlet': 'https://images.unsplash.com/photo-1506084868230-bb9d95c24759?w=400&h=300&fit=crop&auto=format',
    'French Toast': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop&auto=format',
    'Boiled Egg With Avocado': 'https://images.unsplash.com/photo-1571197119282-7c4c2c2c6d10?w=400&h=300&fit=crop&auto=format',
    'Avocado Toast Normal': 'https://images.unsplash.com/photo-1549888834-3ec93abae044?w=400&h=300&fit=crop&auto=format',
    'Avocado Toast Special': 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400&h=300&fit=crop&auto=format',
    'Avocado with Tunna': 'https://images.unsplash.com/photo-1588123575102-d3b6c6afd2c3?w=400&h=300&fit=crop&auto=format',
    
    # Fries & Pancakes
    'French Fries': 'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400&h=300&fit=crop&auto=format',
    'Pan Cake': 'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=300&fit=crop&auto=format',
    'Wafil Kuckis': 'https://images.unsplash.com/photo-1551218808-94e220e084d2?w=400&h=300&fit=crop&auto=format',
    'Ahu Wafil': 'https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=400&h=300&fit=crop&auto=format',
    
    # Traditional Ethiopian Breakfast
    'Ahu Special Breakfast': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop&auto=format',
    'Ahu Special Ertib': 'https://images.unsplash.com/photo-1588123575102-d3b6c6afd2c3?w=400&h=300&fit=crop&auto=format',
    'Half Half Chechebsa': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=300&fit=crop&auto=format',
    'Normal Ertib': 'https://images.unsplash.com/photo-1610057099443-fde8c4d50fbf?w=400&h=300&fit=crop&auto=format',
    'Normal Fetira': 'https://images.unsplash.com/photo-1549888834-3ec93abae044?w=400&h=300&fit=crop&auto=format',
    'Normal Foul': 'https://images.unsplash.com/photo-1588123575102-d3b6c6afd2c3?w=400&h=300&fit=crop&auto=format',
    'Special Chechebsa': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop&auto=format',
    'Special Ertib': 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=400&h=300&fit=crop&auto=format',
    'Special Fetira': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=300&fit=crop&auto=format',
    'Special Foul': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop&auto=format',
    'Yefurno Chechebsa': 'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=300&fit=crop&auto=format',
    'Yeteff Chechebsa': 'https://images.unsplash.com/photo-1506084868230-bb9d95c24759?w=400&h=300&fit=crop&auto=format',
    
    # Extras
    'Extra Avocado': 'https://images.unsplash.com/photo-1570831739435-6601aa3fa4fb?w=400&h=300&fit=crop&auto=format',
    'Extra Bread': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=300&fit=crop&auto=format',
    'Extra Catchup': 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400&h=300&fit=crop&auto=format',
    'Extra Cheese': 'https://images.unsplash.com/photo-1525059696034-4967a729002e?w=400&h=300&fit=crop&auto=format',
    'Extra Honey': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop&auto=format',
    'Extra Kita/Melewa': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=300&fit=crop&auto=format',
    'Extra Mionise': 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400&h=300&fit=crop&auto=format',
    'Extra Tunna': 'https://images.unsplash.com/photo-1626765515755-5839c1e2b29e?w=400&h=300&fit=crop&auto=format'
}

def update_images():
    with app.app_context():
        print("Updating menu item images...")
        updated_count = 0
        
        for name, image_url in image_mappings.items():
            item = MenuItem.query.filter_by(name=name).first()
            if item:
                item.image_url = image_url
                updated_count += 1
                print(f"Updated {name}")
            else:
                print(f"Item not found: {name}")
        
        db.session.commit()
        print(f"\nSuccessfully updated {updated_count} menu item images!")

if __name__ == "__main__":
    update_images()