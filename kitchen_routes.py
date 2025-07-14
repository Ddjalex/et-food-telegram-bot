from flask import request, jsonify, render_template, session, redirect, url_for
from app import app, db
from models import MenuItem, Category, Restaurant, Order
from datetime import datetime
import logging
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Kitchen staff access routes
@app.route('/kitchen')
def kitchen_dashboard():
    """Kitchen staff dashboard"""
    return render_template('kitchen_dashboard.html')

@app.route('/kitchen/menu')
def kitchen_menu_management():
    """Kitchen staff menu management page"""
    return render_template('kitchen_menu_management.html')

# Kitchen API endpoints for menu management
@app.route('/api/kitchen/menu-items', methods=['GET'])
def kitchen_get_menu_items():
    """Get all menu items for kitchen staff"""
    try:
        restaurant_id = request.args.get('restaurant_id', 1)
        menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
        return jsonify({
            'success': True,
            'menu_items': [item.to_dict() for item in menu_items]
        })
    except Exception as e:
        logger.error(f"Error fetching menu items for kitchen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/menu-items', methods=['POST'])
def kitchen_create_menu_item():
    """Create new menu item (kitchen staff)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'price', 'category_id', 'restaurant_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Create new menu item
        menu_item = MenuItem(
            name=data['name'],
            description=data.get('description', ''),
            price=float(data['price']),
            category_id=int(data['category_id']),
            restaurant_id=int(data['restaurant_id']),
            image_url=data.get('image_url', ''),
            available=data.get('available', True)
        )
        
        db.session.add(menu_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item created successfully',
            'menu_item': menu_item.to_dict()
        })
    except Exception as e:
        logger.error(f"Error creating menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/menu-items/<int:item_id>', methods=['PUT'])
def kitchen_update_menu_item(item_id):
    """Update menu item (kitchen staff)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            menu_item.name = data['name']
        if 'description' in data:
            menu_item.description = data['description']
        if 'price' in data:
            menu_item.price = float(data['price'])
        if 'category_id' in data:
            menu_item.category_id = int(data['category_id'])
        if 'image_url' in data:
            menu_item.image_url = data['image_url']
        if 'available' in data:
            menu_item.available = data['available']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item updated successfully',
            'menu_item': menu_item.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/menu-items/<int:item_id>', methods=['DELETE'])
def kitchen_delete_menu_item(item_id):
    """Delete menu item (kitchen staff)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        db.session.delete(menu_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories', methods=['GET'])
def kitchen_get_categories():
    """Get all categories for kitchen staff"""
    try:
        categories = Category.query.all()
        return jsonify({
            'success': True,
            'categories': [category.to_dict() for category in categories]
        })
    except Exception as e:
        logger.error(f"Error fetching categories for kitchen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories', methods=['POST'])
def kitchen_create_category():
    """Create new category (kitchen staff)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Category name is required'}), 400
        
        # Create new category
        category = Category(
            name=data['name'],
            description=data.get('description', ''),
            icon=data.get('icon', '🍽️'),
            image_url=data.get('image_url', ''),
            sort_order=data.get('sort_order', 0)
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category created successfully',
            'category': category.to_dict()
        })
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories/<int:category_id>', methods=['PUT'])
def kitchen_update_category(category_id):
    """Update category (kitchen staff)"""
    try:
        category = Category.query.get_or_404(category_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        if 'icon' in data:
            category.icon = data['icon']
        if 'image_url' in data:
            category.image_url = data['image_url']
        if 'sort_order' in data:
            category.sort_order = int(data['sort_order'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category updated successfully',
            'category': category.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories/<int:category_id>', methods=['DELETE'])
def kitchen_delete_category(category_id):
    """Delete category (kitchen staff)"""
    try:
        category = Category.query.get_or_404(category_id)
        
        # Check if category has menu items
        menu_items_count = MenuItem.query.filter_by(category_id=category_id).count()
        if menu_items_count > 0:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete category with {menu_items_count} menu items. Move or delete items first.'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/upload-image', methods=['POST'])
def kitchen_upload_image():
    """Upload image for menu items or categories"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Invalid file type. Only PNG, JPG, JPEG, GIF, and WebP are allowed.'}), 400
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.static_folder, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Return URL for the uploaded image
        image_url = f"/static/uploads/{filename}"
        
        return jsonify({
            'success': True,
            'image_url': image_url,
            'filename': filename
        })
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/restaurants', methods=['GET'])
def kitchen_get_restaurants():
    """Get all restaurants for kitchen staff"""
    try:
        restaurants = Restaurant.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'restaurants': [restaurant.to_dict() for restaurant in restaurants]
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants for kitchen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500