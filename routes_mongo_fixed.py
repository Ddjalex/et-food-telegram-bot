"""
MongoDB-based Routes for ET-FOOD Delivery System
Main application routes using MongoDB models
"""
from flask import render_template, request, jsonify, redirect, url_for, session, send_from_directory
from app_mongo_fixed import app
from models_mongo_fixed import (
    restaurant_model, menu_item_model, order_model, driver_model, 
    admin_user_model, payment_transaction_model, category_model
)
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Home page"""
    return render_template('webapp_modern.html')

@app.route('/webapp')
def webapp():
    """Main web application interface"""
    return render_template('webapp_modern.html')

@app.route('/api/restaurant-info')
def get_restaurant_info():
    """Get restaurant information"""
    try:
        # Get the first available restaurant
        restaurants = restaurant_model.get_active_restaurants()
        
        if not restaurants:
            return jsonify({
                'success': False,
                'error': 'No restaurants available',
                'company': {
                    'name': 'ET-FOOD',
                    'description': 'Food Delivery Service'
                },
                'restaurant': {
                    'name': 'Restaurant',
                    'description': 'Delicious Food',
                    'logo_url': None,
                    'cover_image_url': None
                }
            })
        
        restaurant = restaurants[0]
        
        return jsonify({
            'success': True,
            'company': {
                'name': 'ET-FOOD',
                'description': 'Food Delivery Service'
            },
            'restaurant': {
                'id': restaurant['id'],
                'name': restaurant['name'],
                'description': restaurant['description'],
                'address': restaurant['address'],
                'phone': restaurant['phone'],
                'logo_url': restaurant['logo_url'],
                'cover_image_url': restaurant['cover_image_url'],
                'estimated_delivery_time': restaurant['estimated_delivery_time']
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching restaurant info: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch restaurant information'
        }), 500

@app.route('/api/menu')
def get_menu():
    """Get menu items for a restaurant"""
    try:
        restaurant_id = request.args.get('restaurant_id')
        category_filter = request.args.get('category')
        
        if not restaurant_id:
            # Get first available restaurant
            restaurants = restaurant_model.get_active_restaurants()
            if restaurants:
                restaurant_id = restaurants[0]['id']
            else:
                return jsonify({
                    'success': False,
                    'error': 'No restaurants available'
                }), 404
        
        # Get menu items
        if category_filter:
            menu_items = menu_item_model.get_by_category(restaurant_id, category_filter)
        else:
            menu_items = menu_item_model.get_by_restaurant(restaurant_id)
        
        return jsonify({
            'success': True,
            'menu_items': menu_items,
            'restaurant_id': restaurant_id
        })
        
    except Exception as e:
        logger.error(f"Error fetching menu: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch menu'
        }), 500

@app.route('/api/categories')
def get_categories():
    """Get all categories"""
    try:
        categories = category_model.get_active_categories()
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch categories'
        }), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['customer_name', 'customer_phone', 'items']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Get restaurant (use first available if not specified)
        restaurant_id = data.get('restaurant_id')
        if not restaurant_id:
            restaurants = restaurant_model.get_active_restaurants()
            if restaurants:
                restaurant_id = restaurants[0]['id']
            else:
                return jsonify({
                    'success': False,
                    'error': 'No restaurants available'
                }), 404
        
        # Create the order
        order_id = order_model.create(
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            restaurant_id=restaurant_id,
            items=data['items'],
            customer_address=data.get('customer_address'),
            telegram_user_id=data.get('telegram_user_id'),
            total_amount=data.get('total_amount', 0.0),
            payment_method=data.get('payment_method', 'cash'),
            location_lat=data.get('location_lat'),
            location_lng=data.get('location_lng'),
            special_instructions=data.get('special_instructions')
        )
        
        # Get the created order
        order = order_model.find_by_id(order_id)
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'order': order,
            'message': 'Order created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create order'
        }), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get orders (admin endpoint)"""
    try:
        restaurant_id = request.args.get('restaurant_id')
        status_filter = request.args.get('status')
        customer_id = request.args.get('customer_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        if customer_id:
            # Get orders for specific customer
            orders = order_model.get_by_customer(customer_id)
        elif restaurant_id:
            # Get orders for specific restaurant
            orders = order_model.get_by_restaurant(restaurant_id, status_filter)
        else:
            # Get all orders
            orders = order_model.find_many()
        
        # Simple pagination (MongoDB skip/limit would be better for large datasets)
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
        logger.error(f"Error fetching orders: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch orders'
        }), 500

# Static file serving
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500