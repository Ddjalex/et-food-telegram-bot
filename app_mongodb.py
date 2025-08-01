"""
Complete MongoDB Flask Application for ET-FOOD Delivery System
This replaces the PostgreSQL version with MongoDB using custom client
"""
import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get("SESSION_SECRET", "et-food-secret-key-2025-mongo-migration")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# MongoDB models (these will be imported after the models are loaded)
from models_final import (
    restaurant_model, menu_item_model, order_model, admin_user_model, 
    driver_model, category_model, payment_transaction_model
)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def check_admin_session():
    """Check if user is logged in as admin"""
    return session.get('admin_logged_in', False)

def allowed_file(filename):
    """Check if file type is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ==============================================================================
# MAIN ROUTES
# ==============================================================================

@app.route('/')
def index():
    """Home page"""
    return render_template('webapp_beu_style.html')

@app.route('/webapp')
def webapp():
    """Main web application interface"""
    return render_template('webapp_beu_style.html')

# ==============================================================================
# API ROUTES
# ==============================================================================

@app.route('/api/restaurant-info')
def get_restaurant_info():
    """Get restaurant information"""
    try:
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
                    'description': 'Delicious Food'
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
                'logo_url': restaurant.get('logo_url'),
                'cover_image_url': restaurant.get('cover_image_url'),
                'estimated_delivery_time': restaurant['estimated_delivery_time']
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching restaurant info: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch restaurant information'
        }), 500

@app.route('/api/restaurants')
def get_restaurants():
    """Get all restaurants with menu counts for webapp"""
    try:
        restaurants = restaurant_model.get_active_restaurants()
        
        formatted_restaurants = []
        for restaurant in restaurants:
            restaurant_id = restaurant['id']
            
            # Count available menu items
            menu_items_count = menu_item_model.count({'restaurant_id': restaurant_id, 'available': True})
            
            formatted_restaurants.append({
                'id': restaurant_id,
                'name': restaurant['name'],
                'description': restaurant.get('description', ''),
                'address': restaurant.get('address', ''),
                'phone': restaurant.get('phone', ''),
                'logo_url': restaurant.get('logo_url'),
                'cover_image_url': restaurant.get('cover_image_url'),
                'estimated_delivery_time': restaurant.get('estimated_delivery_time', '30-45 minutes'),
                'delivery_fee': restaurant.get('delivery_fee', 0.0),
                'minimum_order': restaurant.get('minimum_order', 0.0),
                'is_active': restaurant.get('is_active', True),
                'menu_items_count': menu_items_count,
                'rating': restaurant.get('rating', 4.5),
                'is_featured': restaurant.get('is_featured', False)
            })
        
        return jsonify({
            'success': True,
            'restaurants': formatted_restaurants,
            'total': len(formatted_restaurants)
        })
        
    except Exception as e:
        logger.error(f"Error fetching restaurants: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch restaurants'
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
    """Get orders"""
    try:
        restaurant_id = request.args.get('restaurant_id')
        status_filter = request.args.get('status')
        customer_id = request.args.get('customer_id')
        
        if customer_id:
            # Get orders for specific customer
            orders = order_model.get_by_customer(customer_id)
        elif restaurant_id:
            # Get orders for specific restaurant
            orders = order_model.get_by_restaurant(restaurant_id, status_filter)
        else:
            # Get all orders
            orders = order_model.find_many()
        
        return jsonify({
            'success': True,
            'orders': orders,
            'total': len(orders)
        })
        
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch orders'
        }), 500

# ==============================================================================
# ADMIN ROUTES
# ==============================================================================

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
        
        if admin_user and admin_user.get('password') == password:  # Simple password check for demo
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

@app.route('/superadmin')
@app.route('/superadmin/')
def super_admin_dashboard():
    """Super admin dashboard"""
    if not check_admin_session():
        return redirect(url_for('super_admin_login'))
    
    try:
        # Get current admin user
        admin_user = admin_user_model.find_by_id(session.get('admin_user_id'))
        
        # Get comprehensive statistics
        stats = {
            'total_orders': order_model.count(),
            'total_restaurants': restaurant_model.count(),
            'total_drivers': driver_model.count(),
            'total_admins': admin_user_model.count()
        }
        
        return render_template('super_admin_dashboard.html', stats=stats, admin=admin_user)
        
    except Exception as e:
        logger.error(f"Error loading super admin dashboard: {e}")
        # Create default admin object if none found
        default_admin = {'username': 'superadmin', 'full_name': 'Super Administrator'}
        return render_template('super_admin_dashboard.html', stats={}, admin=default_admin)

@app.route('/superadmin/login', methods=['GET', 'POST'])
def super_admin_login():
    """Super admin login page"""
    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        if not username or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username and password are required'}), 400
            return render_template('superadmin_login.html', error='Username and password are required')
        
        # Find admin user
        admin_user = admin_user_model.find_by_username(username)
        
        if admin_user and admin_user.get('password') == password and admin_user.get('role') == 'superadmin':
            session['admin_logged_in'] = True
            session['admin_user_id'] = admin_user['id']
            session['admin_username'] = admin_user['username']
            session['admin_role'] = 'superadmin'
            
            # Update last login
            admin_user_model.update_last_login(admin_user['id'])
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/superadmin'})
            return redirect(url_for('super_admin_dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid credentials or insufficient privileges'}), 401
            return render_template('superadmin_login.html', error='Invalid credentials or insufficient privileges')
    
    return render_template('superadmin_login.html')



# ==============================================================================
# SUPER ADMIN API ROUTES
# ==============================================================================

@app.route('/api/restaurants/super-admin')
def get_restaurants_super_admin():
    """Get all restaurants for super admin dashboard with accurate menu items count"""
    try:
        if not session.get('admin_logged_in') or session.get('admin_role') != 'superadmin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        restaurants = restaurant_model.get_all_restaurants()
        
        # Format restaurants for dashboard with accurate counts
        formatted_restaurants = []
        for restaurant in restaurants:
            restaurant_id = restaurant['id']
            
            # Calculate accurate menu items count
            menu_items_count = menu_item_model.count({'restaurant_id': restaurant_id, 'available': True})
            total_menu_items = menu_item_model.count({'restaurant_id': restaurant_id})
            
            # Calculate orders for today
            today = datetime.now().strftime('%Y-%m-%d')
            orders_today = order_model.count({
                'restaurant_id': restaurant_id,
                'created_at': {'$gte': today}
            })
            
            # Calculate total orders for this restaurant
            total_orders = order_model.count({'restaurant_id': restaurant_id})
            
            formatted_restaurants.append({
                'id': restaurant_id,
                'name': restaurant['name'],
                'description': restaurant['description'],
                'address': restaurant['address'],
                'phone': restaurant['phone'],
                'logo_url': restaurant.get('logo_url'),
                'cover_image_url': restaurant.get('cover_image_url'),
                'estimated_delivery_time': restaurant['estimated_delivery_time'],
                'is_active': restaurant.get('is_active', True),
                'created_at': restaurant.get('created_at', ''),
                'menu_items_count': menu_items_count,
                'total_menu_items': total_menu_items,
                'orders_today': orders_today,
                'total_orders': total_orders,
                'delivery_fee': restaurant.get('delivery_fee', 0.0),
                'minimum_order': restaurant.get('minimum_order', 0.0)
            })
        
        return jsonify({
            'success': True,
            'restaurants': formatted_restaurants,
            'total_restaurants': len(formatted_restaurants)
        })
        
    except Exception as e:
        logger.error(f"Error fetching restaurants for super admin: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch restaurants'
        }), 500

@app.route('/api/super-admin/admins')
def get_admins_super_admin():
    """Get all admin users for super admin dashboard"""
    try:
        if not session.get('admin_logged_in') or session.get('admin_role') != 'superadmin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        admins = admin_user_model.get_all_admins()
        
        # Format admins for dashboard
        formatted_admins = []
        for admin in admins:
            formatted_admins.append({
                'id': admin['id'],
                'username': admin['username'],
                'role': admin.get('role', 'admin'),
                'restaurant_id': admin.get('restaurant_id'),
                'restaurant_name': admin.get('restaurant_name', 'N/A'),
                'is_active': admin.get('is_active', True),
                'last_login': admin.get('last_login', 'Never'),
                'created_at': admin.get('created_at', '')
            })
        
        return jsonify({
            'success': True,
            'admins': formatted_admins
        })
        
    except Exception as e:
        logger.error(f"Error fetching admins for super admin: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch admins'
        }), 500

@app.route('/api/super-admin/drivers')
def get_drivers_super_admin():
    """Get all drivers for super admin dashboard"""
    try:
        if not session.get('admin_logged_in') or session.get('admin_role') != 'superadmin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        drivers = driver_model.get_all_drivers()
        
        # Format drivers for dashboard
        formatted_drivers = []
        for driver in drivers:
            formatted_drivers.append({
                'id': driver['id'],
                'name': driver['name'],
                'phone': driver['phone'],
                'vehicle_type': driver.get('vehicle_type', 'Unknown'),
                'is_approved': driver.get('is_approved', False),
                'is_active': driver.get('is_active', True),
                'location_lat': driver.get('location_lat'),
                'location_lng': driver.get('location_lng'),
                'last_location_update': driver.get('last_location_update', 'Never'),
                'created_at': driver.get('created_at', '')
            })
        
        return jsonify({
            'success': True,
            'drivers': formatted_drivers
        })
        
    except Exception as e:
        logger.error(f"Error fetching drivers for super admin: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch drivers'
        }), 500

@app.route('/api/super-admin/stats')
def get_super_admin_stats():
    """Get dashboard statistics for super admin"""
    try:
        if not session.get('admin_logged_in') or session.get('admin_role') != 'superadmin':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        stats = {
            'total_restaurants': restaurant_model.count(),
            'total_menu_items': menu_item_model.count(),
            'total_orders': order_model.count(),
            'total_drivers': driver_model.count(),
            'total_admins': admin_user_model.count(),
            'pending_drivers': driver_model.count_pending(),
            'active_drivers': driver_model.count_active(),
            'orders_today': order_model.count_today(),
            'revenue_today': 0  # Will implement later
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error fetching super admin stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch statistics'
        }), 500

# ==============================================================================
# STATIC FILE SERVING
# ==============================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(app.static_folder, filename)

# ==============================================================================
# ERROR HANDLERS
# ==============================================================================

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

# ==============================================================================
# INITIALIZATION
# ==============================================================================

def init_application():
    """Initialize the application"""
    try:
        logger.info("📊 MongoDB Application Statistics:")
        logger.info(f"   Restaurants: {restaurant_model.count()}")
        logger.info(f"   Menu Items: {menu_item_model.count()}")
        logger.info(f"   Categories: {category_model.count()}")
        logger.info(f"   Admin Users: {admin_user_model.count()}")
        logger.info(f"   Orders: {order_model.count()}")
        logger.info(f"   Drivers: {driver_model.count()}")
        logger.info("🎉 MongoDB ET-FOOD Application ready!")
        
    except Exception as e:
        logger.error(f"❌ Application initialization error: {e}")

# Initialize when app starts
with app.app_context():
    init_application()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)