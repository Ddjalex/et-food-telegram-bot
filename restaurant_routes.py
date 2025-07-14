from flask import request, jsonify, render_template, session, redirect, url_for
from app import app, db
from models import Restaurant, MenuItem, Order, AdminUser
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@app.route('/api/restaurants', methods=['GET'])
def get_restaurants():
    """Get all active restaurants for customer selection"""
    try:
        restaurants = Restaurant.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'restaurants': [restaurant.to_dict() for restaurant in restaurants]
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/select-restaurant')
def select_restaurant():
    """Restaurant selection page"""
    return render_template('select_restaurant.html')

@app.route('/api/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    """Get menu items for a specific restaurant"""
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        if not restaurant.is_active:
            return jsonify({'success': False, 'error': 'Restaurant not active'}), 404
        
        menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id, available=True).all()
        return jsonify({
            'success': True,
            'restaurant': restaurant.to_dict(),
            'menu_items': [item.to_dict() for item in menu_items]
        })
    except Exception as e:
        logger.error(f"Error fetching menu for restaurant {restaurant_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/restaurants', methods=['GET'])
def admin_get_restaurants():
    """Admin endpoint to get all restaurants"""
    try:
        restaurants = Restaurant.query.all()
        return jsonify({
            'success': True,
            'restaurants': [restaurant.to_dict() for restaurant in restaurants]
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants for admin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/restaurants', methods=['POST'])
def admin_create_restaurant():
    """Admin endpoint to create a new restaurant"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'address', 'phone']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Create new restaurant
        restaurant = Restaurant(
            name=data['name'],
            description=data['description'],
            address=data['address'],
            phone=data['phone'],
            latitude=data.get('latitude', 9.0579),
            longitude=data.get('longitude', 38.7914),
            logo_url=data.get('logo_url'),
            cover_image_url=data.get('cover_image_url'),
            is_active=data.get('is_active', True),
            is_featured=data.get('is_featured', False),
            delivery_fee=data.get('delivery_fee', 0.0),
            minimum_order=data.get('minimum_order', 0.0),
            estimated_delivery_time=data.get('estimated_delivery_time', '30-45 minutes'),
            opening_hours=data.get('opening_hours', {
                'monday': '09:00-22:00',
                'tuesday': '09:00-22:00',
                'wednesday': '09:00-22:00',
                'thursday': '09:00-22:00',
                'friday': '09:00-22:00',
                'saturday': '09:00-22:00',
                'sunday': '09:00-22:00'
            })
        )
        
        db.session.add(restaurant)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Restaurant created successfully',
            'restaurant': restaurant.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error creating restaurant: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/restaurants/<int:restaurant_id>', methods=['PUT'])
def admin_update_restaurant(restaurant_id):
    """Admin endpoint to update a restaurant"""
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        data = request.get_json()
        
        # Update fields
        for field in ['name', 'description', 'address', 'phone', 'latitude', 'longitude', 
                     'logo_url', 'cover_image_url', 'is_active', 'is_featured', 
                     'delivery_fee', 'minimum_order', 'estimated_delivery_time', 'opening_hours']:
            if field in data:
                setattr(restaurant, field, data[field])
        
        restaurant.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Restaurant updated successfully',
            'restaurant': restaurant.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error updating restaurant {restaurant_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/restaurants/<int:restaurant_id>', methods=['DELETE'])
def admin_delete_restaurant(restaurant_id):
    """Admin endpoint to delete a restaurant"""
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        
        # Check if restaurant has orders
        order_count = Order.query.filter_by(restaurant_id=restaurant_id).count()
        if order_count > 0:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete restaurant with {order_count} orders. Deactivate instead.'
            }), 400
        
        # Check if restaurant has menu items
        menu_count = MenuItem.query.filter_by(restaurant_id=restaurant_id).count()
        if menu_count > 0:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete restaurant with {menu_count} menu items. Remove menu items first.'
            }), 400
        
        db.session.delete(restaurant)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Restaurant deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting restaurant {restaurant_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/restaurants/<int:restaurant_id>/toggle-status', methods=['POST'])
def admin_toggle_restaurant_status(restaurant_id):
    """Admin endpoint to toggle restaurant active status"""
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        restaurant.is_active = not restaurant.is_active
        restaurant.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'activated' if restaurant.is_active else 'deactivated'
        return jsonify({
            'success': True,
            'message': f'Restaurant {status} successfully',
            'restaurant': restaurant.to_dict()
        })
    
    except Exception as e:
        logger.error(f"Error toggling restaurant {restaurant_id} status: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/restaurants')
def admin_restaurants():
    """Admin page for restaurant management"""
    return render_template('admin_restaurants.html')

