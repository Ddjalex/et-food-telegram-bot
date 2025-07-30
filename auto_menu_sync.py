#!/usr/bin/env python3
"""
Automatic Menu Synchronization System
This script automatically runs during app startup to ensure database and files are always in sync
Solves the environment persistence issue
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_and_sync_menu():
    """Check if menu needs to be synced and do it automatically"""
    try:
        from app import app, db
        from models import Restaurant, MenuItem
        
        with app.app_context():
            # Count uploaded images
            upload_dir = 'static/uploads'
            if os.path.exists(upload_dir):
                image_files = []
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.JPG', '*.JPEG', '*.PNG', '*.WEBP']:
                    import glob
                    image_files.extend(glob.glob(os.path.join(upload_dir, ext)))
                
                image_count = len(image_files)
            else:
                image_count = 0
            
            # Count menu items
            menu_count = MenuItem.query.count()
            
            print(f"🔍 Menu sync check: {image_count} images, {menu_count} menu items")
            
            # If we have significantly more images than menu items, restore menu
            if image_count > menu_count + 10:  # Allow some tolerance
                print(f"📦 Detected {image_count} images but only {menu_count} menu items")
                print("🔄 Auto-syncing menu with uploaded images...")
                
                # Import and run the restoration
                from restore_complete_menu_with_images import restore_complete_menu
                success = restore_complete_menu()
                
                if success:
                    print("✅ Menu auto-sync completed successfully!")
                    return True
                else:
                    print("❌ Menu auto-sync failed")
                    return False
            else:
                print("✅ Menu is already in sync")
                return True
                
    except Exception as e:
        print(f"⚠️ Menu sync check failed: {e}")
        return False

if __name__ == "__main__":
    check_and_sync_menu()