"""
MongoDB-based Admin Routes for ET-FOOD Delivery System
Administrative interface routes using MongoDB models
"""
from flask import render_template, request, jsonify, redirect, url_for, session
from app_mongo import app
from models_mongo import (
    restaurant_model, menu_item_model, order_model, driver_model,
    admin_user_model, payment_transaction_model, category_model
)
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
import os

logger = logging.getLogger(__name__)

# Admin Authentication
def check_admin_session():
    """Check if user is logged in as admin"""
    return session.get('admin_logged_in', False)

@app.route('/admin')
@app.route('/admin/')
def admin_dashboard():
    """Main admin dashboard"""
    if not check_admin_session():
        return redirect(url_for('admin_login'))
    
    try:
        # Get dashboard statistics
        stats = {
            'total_orders': order_model.count(),
            'pending_orders': order_model.count({'status': 'pending'}),
            'total_restaurants': restaurant_model.count(),
            'total_drivers': driver_model.count(),
            'active_drivers': driver_model.count({'is_active': True, 'is_available': True})
        }
        
        return render_template('admin.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        return render_template('admin.html', stats={})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('admin_login.html', error='Username and password are required')
        
        # Find admin user
        admin_user = admin_user_model.find_by_username(username)
        
        if admin_user and admin_user['password_hash'] == password:  # In production, use proper password hashing
            session['admin_logged_in'] = True
            session['admin_user_id'] = admin_user['id']
            session['admin_username'] = admin_user['username']
            session['admin_role'] = admin_user.get('role', 'admin')
            
            # Update last login
            admin_user_model.update_last_login(admin_user['id'])
            
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid username or password')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.clear()
    return redirect(url_for('admin_login'))

# Restaurant Management
@app.route('/api/admin/restaurants', methods=['GET'])
def get_admin_restaurants():
    """Get all restaurants for admin"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        restaurants = restaurant_model.find_many()
        return jsonify({
            'success': True,
            'restaurants': restaurants
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch restaurants'}), 500

@app.route('/api/admin/restaurants', methods=['POST'])
def create_admin_restaurant():
    """Create a new restaurant"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        restaurant_id = restaurant_model.create(
            name=data['name'],
            description=data.get('description'),
            address=data.get('address'),
            phone=data.get('phone'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            estimated_delivery_time=data.get('estimated_delivery_time', '30-45 minutes')
        )
        
        return jsonify({
            'success': True,
            'restaurant_id': restaurant_id,
            'message': 'Restaurant created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating restaurant: {e}")
        return jsonify({'success': False, 'error': 'Failed to create restaurant'}), 500

@app.route('/api/admin/restaurants/<restaurant_id>', methods=['PUT'])
def update_admin_restaurant(restaurant_id):
    """Update a restaurant"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        success = restaurant_model.update_by_id(restaurant_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Restaurant updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Restaurant not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error updating restaurant: {e}")
        return jsonify({'success': False, 'error': 'Failed to update restaurant'}), 500

# Menu Item Management
@app.route('/api/admin/menu-items', methods=['GET'])
def get_admin_menu_items():
    """Get menu items for admin"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        restaurant_id = request.args.get('restaurant_id')
        
        if restaurant_id:
            menu_items = menu_item_model.get_by_restaurant(restaurant_id, available_only=False)
        else:
            menu_items = menu_item_model.find_many()
        
        return jsonify({
            'success': True,
            'menu_items': menu_items
        })
        
    except Exception as e:
        logger.error(f"Error fetching menu items: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch menu items'}), 500

@app.route('/api/admin/menu-items', methods=['POST'])
def create_admin_menu_item():
    """Create a new menu item"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        required_fields = ['name', 'price', 'restaurant_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        menu_item_id = menu_item_model.create(
            name=data['name'],
            price=data['price'],
            restaurant_id=data['restaurant_id'],
            description=data.get('description'),
            category=data.get('category', 'main'),
            image_url=data.get('image_url')
        )
        
        return jsonify({
            'success': True,
            'menu_item_id': menu_item_id,
            'message': 'Menu item created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating menu item: {e}")
        return jsonify({'success': False, 'error': 'Failed to create menu item'}), 500

@app.route('/api/admin/menu-items/<item_id>', methods=['PUT'])
def update_admin_menu_item(item_id):
    """Update a menu item"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        
        success = menu_item_model.update_by_id(item_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Menu item updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Menu item not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error updating menu item: {e}")
        return jsonify({'success': False, 'error': 'Failed to update menu item'}), 500

@app.route('/api/admin/menu-items/<item_id>', methods=['DELETE'])
def delete_admin_menu_item(item_id):
    """Delete a menu item"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        success = menu_item_model.delete_by_id(item_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Menu item deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Menu item not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error deleting menu item: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete menu item'}), 500

# Driver Management
@app.route('/api/admin/drivers', methods=['GET'])
def get_admin_drivers():
    """Get all drivers for admin"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        drivers = driver_model.find_many()
        return jsonify({
            'success': True,
            'drivers': drivers
        })
        
    except Exception as e:
        logger.error(f"Error fetching drivers: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch drivers'}), 500

@app.route('/api/admin/drivers/<driver_id>/approve', methods=['PUT'])
def approve_driver(driver_id):
    """Approve a driver"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        success = driver_model.update_by_id(driver_id, {'is_approved': True})
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Driver approved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Driver not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error approving driver: {e}")
        return jsonify({'success': False, 'error': 'Failed to approve driver'}), 500

# Order Management
@app.route('/api/admin/orders', methods=['GET'])
def get_admin_orders():
    """Get orders for admin with advanced filtering"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        restaurant_id = request.args.get('restaurant_id')
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        filter_dict = {}
        if restaurant_id:
            filter_dict['restaurant_id'] = restaurant_id
        if status:
            filter_dict['status'] = status
        
        # Get orders with filter
        orders = order_model.find_many(filter_dict, sort=[('created_at', -1)])
        
        # Simple pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_orders = orders[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'orders': paginated_orders,
            'total': len(orders),
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Error fetching admin orders: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch orders'}), 500

# Payment Management
@app.route('/api/admin/payments', methods=['GET'])
def get_admin_payments():
    """Get payment transactions for admin"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        order_id = request.args.get('order_id')
        
        if order_id:
            payments = payment_transaction_model.get_by_order(order_id)
        else:
            payments = payment_transaction_model.find_many(sort=[('created_at', -1)])
        
        return jsonify({
            'success': True,
            'payments': payments
        })
        
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch payments'}), 500

# Dashboard Statistics
@app.route('/api/admin/stats')
def get_admin_stats():
    """Get admin dashboard statistics"""
    if not check_admin_session():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        stats = {
            'total_orders': order_model.count(),
            'pending_orders': order_model.count({'status': 'pending'}),
            'confirmed_orders': order_model.count({'status': 'confirmed'}),
            'preparing_orders': order_model.count({'status': 'preparing'}),
            'out_for_delivery_orders': order_model.count({'status': 'out_for_delivery'}),
            'delivered_orders': order_model.count({'status': 'delivered'}),
            'cancelled_orders': order_model.count({'status': 'cancelled'}),
            'total_restaurants': restaurant_model.count(),
            'active_restaurants': restaurant_model.count({'is_active': True}),
            'total_drivers': driver_model.count(),
            'active_drivers': driver_model.count({'is_active': True}),
            'available_drivers': driver_model.count({'is_active': True, 'is_available': True}),
            'approved_drivers': driver_model.count({'is_approved': True}),
            'total_menu_items': menu_item_model.count(),
            'available_menu_items': menu_item_model.count({'available': True})
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch statistics'}), 500

# Super Admin Routes
@app.route('/superadmin')
@app.route('/superadmin/')
def super_admin_dashboard():
    """Super admin dashboard"""
    if not check_admin_session():
        return redirect(url_for('super_admin_login'))
    
    try:
        # Get comprehensive statistics
        stats = {
            'total_orders': order_model.count(),
            'total_restaurants': restaurant_model.count(),
            'total_drivers': driver_model.count(),
            'total_admins': admin_user_model.count()
        }
        
        return render_template('super_admin_dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error loading super admin dashboard: {e}")
        return render_template('super_admin_dashboard.html', stats={})

@app.route('/superadmin/login', methods=['GET', 'POST'])
def super_admin_login():
    """Super admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('superadmin_login.html', error='Username and password are required')
        
        # Find admin user
        admin_user = admin_user_model.find_by_username(username)
        
        if admin_user and admin_user['password_hash'] == password and admin_user.get('role') == 'super_admin':
            session['admin_logged_in'] = True
            session['admin_user_id'] = admin_user['id']
            session['admin_username'] = admin_user['username']
            session['admin_role'] = 'super_admin'
            
            # Update last login
            admin_user_model.update_last_login(admin_user['id'])
            
            return redirect(url_for('super_admin_dashboard'))
        else:
            return render_template('superadmin_login.html', error='Invalid credentials or insufficient privileges')
    
    return render_template('superadmin_login.html')