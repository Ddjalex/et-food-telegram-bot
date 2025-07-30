#!/usr/bin/env python3
"""
Automatic Data Backup & Persistence Script
Ensures all your data changes are saved and protected
"""

import os
import json
import shutil
from datetime import datetime
from app import app, db
from models import Restaurant, MenuItem, Category, AdminUser, Order

def backup_database_data():
    """Backup all database data to JSON files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"data_backups/{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    with app.app_context():
        # Backup restaurants
        restaurants = Restaurant.query.all()
        restaurant_data = [r.to_dict() if hasattr(r, 'to_dict') else {
            'id': r.id, 'name': r.name, 'description': r.description,
            'address': r.address, 'phone': r.phone, 'is_active': r.is_active
        } for r in restaurants]
        
        # Backup menu items with real image paths
        menu_items = MenuItem.query.all()
        menu_data = [{
            'id': m.id, 'name': m.name, 'price': float(m.price),
            'description': m.description, 'image_url': m.image_url,
            'category': m.category, 'available': m.available,
            'restaurant_id': m.restaurant_id
        } for m in menu_items]
        
        # Backup categories
        categories = Category.query.all()
        category_data = [c.to_dict() if hasattr(c, 'to_dict') else {
            'id': c.id, 'name': c.name, 'description': c.description
        } for c in categories]
        
        # Save to JSON files
        with open(f"{backup_dir}/restaurants.json", 'w') as f:
            json.dump(restaurant_data, f, indent=2)
            
        with open(f"{backup_dir}/menu_items.json", 'w') as f:
            json.dump(menu_data, f, indent=2)
            
        with open(f"{backup_dir}/categories.json", 'w') as f:
            json.dump(category_data, f, indent=2)
    
    # Backup uploaded images
    if os.path.exists('static/uploads'):
        shutil.copytree('static/uploads', f"{backup_dir}/uploads")
    
    print(f"✅ Database backup created: {backup_dir}")
    return backup_dir

def restore_database_data(backup_dir):
    """Restore database data from backup"""
    if not os.path.exists(backup_dir):
        print(f"❌ Backup directory not found: {backup_dir}")
        return False
    
    with app.app_context():
        try:
            # Restore restaurants
            if os.path.exists(f"{backup_dir}/restaurants.json"):
                with open(f"{backup_dir}/restaurants.json", 'r') as f:
                    restaurant_data = json.load(f)
                    for r_data in restaurant_data:
                        existing = Restaurant.query.get(r_data['id'])
                        if not existing:
                            restaurant = Restaurant(**r_data)
                            db.session.add(restaurant)
            
            # Restore menu items
            if os.path.exists(f"{backup_dir}/menu_items.json"):
                with open(f"{backup_dir}/menu_items.json", 'r') as f:
                    menu_data = json.load(f)
                    for m_data in menu_data:
                        existing = MenuItem.query.get(m_data['id'])
                        if not existing:
                            menu_item = MenuItem(**m_data)
                            db.session.add(menu_item)
                        else:
                            # Update existing with backed up data
                            for key, value in m_data.items():
                                if hasattr(existing, key):
                                    setattr(existing, key, value)
            
            # Restore categories
            if os.path.exists(f"{backup_dir}/categories.json"):
                with open(f"{backup_dir}/categories.json", 'r') as f:
                    category_data = json.load(f)
                    for c_data in category_data:
                        existing = Category.query.get(c_data['id'])
                        if not existing:
                            category = Category(**c_data)
                            db.session.add(category)
            
            db.session.commit()
            print("✅ Database restored successfully")
            
            # Restore uploaded images
            if os.path.exists(f"{backup_dir}/uploads"):
                if os.path.exists('static/uploads'):
                    shutil.rmtree('static/uploads')
                shutil.copytree(f"{backup_dir}/uploads", 'static/uploads')
                print("✅ Images restored successfully")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error restoring data: {e}")
            return False

def verify_data_integrity():
    """Verify all data is properly saved"""
    with app.app_context():
        restaurants = Restaurant.query.count()
        menu_items = MenuItem.query.count()
        items_with_images = MenuItem.query.filter(MenuItem.image_url.like('/static/uploads/%')).count()
        categories = Category.query.count()
        
        print(f"📊 Current Data Status:")
        print(f"   - Restaurants: {restaurants}")
        print(f"   - Menu Items: {menu_items}")
        print(f"   - Items with real images: {items_with_images}")
        print(f"   - Categories: {categories}")
        
        # Check image files exist
        missing_images = []
        menu_items_obj = MenuItem.query.all()
        for item in menu_items_obj:
            if item.image_url and item.image_url.startswith('/static/uploads/'):
                image_path = item.image_url[1:]  # Remove leading slash
                if not os.path.exists(image_path):
                    missing_images.append(item.image_url)
        
        if missing_images:
            print(f"⚠️  Missing image files: {len(missing_images)}")
            for img in missing_images[:5]:  # Show first 5
                print(f"     - {img}")
        else:
            print("✅ All image files exist")
        
        return {
            'restaurants': restaurants,
            'menu_items': menu_items,
            'items_with_images': items_with_images,
            'categories': categories,
            'missing_images': len(missing_images)
        }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "backup":
            backup_database_data()
        elif sys.argv[1] == "restore" and len(sys.argv) > 2:
            restore_database_data(sys.argv[2])
        elif sys.argv[1] == "verify":
            verify_data_integrity()
        else:
            print("Usage: python auto_save_data.py [backup|restore <backup_dir>|verify]")
    else:
        # Default: verify current state
        verify_data_integrity()