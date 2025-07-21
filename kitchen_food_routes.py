from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import MenuItem, Restaurant, Order, AdminUser
from datetime import datetime, timedelta
from sqlalchemy import func
import logging
import os
import json
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from functools import wraps

logger = logging.getLogger(__name__)

def kitchen_staff_required(f):
    """Decorator to require kitchen staff or admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('kitchen_login'))
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or not admin.is_active:
            session.clear()
            return redirect(url_for('kitchen_login'))
        
        # Allow kitchen staff and admins to access kitchen dashboard
        if admin.role not in ['kitchen_staff', 'admin', 'super_admin']:
            flash('Access denied. Kitchen staff privileges required.', 'error')
            return redirect(url_for('kitchen_login'))
        
        return f(*args, **kwargs)
    return decorated_function

# Kitchen Food Management Routes
@app.route('/kitchen/food-management')
@kitchen_staff_required
def kitchen_food_management():
    """Kitchen staff food product management page"""
    return render_template('kitchen_food_management.html')

@app.route('/api/menu', methods=['GET'])
def get_menu_items():
    """Get all menu items - accessible for kitchen staff"""
    try:
        restaurant_id = request.args.get('restaurant_id', 1)
        menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
        
        # Convert to simple array format that the kitchen interface expects
        items_list = [item.to_dict() for item in menu_items]
        
        return jsonify({
            'success': True,
            'menu_items': items_list,
            'total_items': len(items_list)
        })
    except Exception as e:
        logger.error(f"Error fetching menu items: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories', methods=['GET'])
def kitchen_get_categories():
    """Get all categories"""
    try:
        # Get unique categories from menu items
        categories = db.session.query(MenuItem.category).distinct().all()
        category_list = [{'name': cat[0]} for cat in categories if cat[0]]
        
        # Add "All" category at the beginning
        category_list.insert(0, {'name': 'All'})
        
        return jsonify({
            'success': True,
            'categories': category_list
        })
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/menu', methods=['POST'])
@kitchen_staff_required
def kitchen_create_menu_item():
    """Create new menu item (kitchen staff only)"""
    try:
        # Handle file upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create timestamp prefix to avoid filename conflicts
                timestamp = str(int(datetime.utcnow().timestamp()))
                filename = f"{timestamp}_{filename}"
                
                # Ensure uploads directory exists
                upload_dir = os.path.join('static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                image_url = f"/static/uploads/{filename}"
        
        # Get form data
        name = request.form.get('name')
        price = request.form.get('price')
        category = request.form.get('category')
        description = request.form.get('description', '')
        available = request.form.get('available', 'true') == 'true'
        image_url_form = request.form.get('image_url')
        
        # Use uploaded image or URL
        if not image_url and image_url_form:
            image_url = image_url_form
        
        # Validate required fields
        if not all([name, price, category]):
            return jsonify({'success': False, 'message': 'Name, price, and category are required'}), 400
        
        # Create new menu item
        menu_item = MenuItem(
            name=name,
            price=float(price),
            category=category,
            description=description,
            image_url=image_url,
            available=available,
            restaurant_id=1  # Default to first restaurant
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
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/kitchen/menu/<int:item_id>', methods=['PUT'])
@kitchen_staff_required
def kitchen_update_menu_item(item_id):
    """Update menu item (kitchen staff only)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        
        # Handle file upload
        image_url = menu_item.image_url  # Keep existing image by default
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create timestamp prefix to avoid filename conflicts
                timestamp = str(int(datetime.utcnow().timestamp()))
                filename = f"{timestamp}_{filename}"
                
                # Ensure uploads directory exists
                upload_dir = os.path.join('static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                image_url = f"/static/uploads/{filename}"
        
        # Get form data
        name = request.form.get('name')
        price = request.form.get('price')
        category = request.form.get('category')
        description = request.form.get('description', '')
        available = request.form.get('available', 'true') == 'true'
        image_url_form = request.form.get('image_url')
        
        # Use uploaded image or URL
        if not image_url and image_url_form:
            image_url = image_url_form
        
        # Update fields
        if name:
            menu_item.name = name
        if price:
            menu_item.price = float(price)
        if category:
            menu_item.category = category
        if description is not None:
            menu_item.description = description
        if image_url:
            menu_item.image_url = image_url
        menu_item.available = available
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item updated successfully',
            'menu_item': menu_item.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/kitchen/menu/<int:item_id>/availability', methods=['PUT'])
@kitchen_staff_required
def kitchen_toggle_menu_item_availability(item_id):
    """Toggle menu item availability (kitchen staff only)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        data = request.get_json()
        
        menu_item.available = data.get('available', not menu_item.available)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Menu item {"enabled" if menu_item.available else "disabled"} successfully',
            'menu_item': menu_item.to_dict()
        })
    except Exception as e:
        logger.error(f"Error toggling menu item availability: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/kitchen/menu/<int:item_id>', methods=['DELETE'])
@kitchen_staff_required
def kitchen_delete_menu_item(item_id):
    """Delete menu item (kitchen staff only)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        
        # Check if item is used in any pending orders
        pending_orders = Order.query.filter(
            Order.status.in_(['pending', 'confirmed', 'preparing'])
        ).all()
        
        # Check if this item is in any pending orders
        for order in pending_orders:
            items = order.items
            if isinstance(items, str):
                import json
                try:
                    items = json.loads(items)
                except:
                    items = []
            
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get('id') == item_id:
                        return jsonify({
                            'success': False, 
                            'message': 'Cannot delete item that is part of pending orders'
                        }), 400
        
        db.session.delete(menu_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Additional Kitchen Routes
@app.route('/kitchen/orders')
@kitchen_staff_required
def kitchen_orders():
    """Kitchen staff orders management page"""
    return render_template('kitchen_orders.html')

@app.route('/kitchen/analytics')
@kitchen_staff_required
def kitchen_analytics():
    """Kitchen staff analytics page"""
    return render_template('kitchen_analytics.html')

@app.route('/kitchen/settings')
@kitchen_staff_required
def kitchen_settings():
    """Kitchen staff settings page"""
    return render_template('kitchen_settings.html')

# Kitchen API endpoints moved to kitchen_availability_routes.py to avoid duplicates

# Kitchen dashboard route
@app.route('/kitchen')
@kitchen_staff_required
def kitchen_dashboard():
    """Kitchen staff dashboard - requires authentication"""
    return render_template('kitchen_dashboard_simple.html')

# Kitchen login route (simplified)
@app.route('/kitchen/login', methods=['GET', 'POST'])
def kitchen_login():
    """Kitchen staff login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('kitchen_login.html')
        
        admin = AdminUser.query.filter_by(username=username).first()
        
        if admin and admin.password_hash and check_password_hash(admin.password_hash, password):
            if not admin.is_active:
                flash('Account is deactivated', 'error')
                return render_template('kitchen_login.html')
            
            # Check if user has kitchen access
            if admin.role not in ['kitchen_staff', 'admin', 'super_admin']:
                flash('No kitchen access permissions', 'error')
                return render_template('kitchen_login.html')
            
            session['admin_id'] = admin.id
            session['admin_role'] = admin.role
            
            # Update last login
            admin.last_login = datetime.utcnow()
            db.session.commit()
            
            return redirect('/kitchen/food-management')
        
        flash('Invalid credentials', 'error')
        return render_template('kitchen_login.html')
    
    return render_template('kitchen_login.html')

@app.route('/kitchen/logout')
def kitchen_logout():
    """Kitchen staff logout"""
    session.clear()
    return redirect('/kitchen/login')