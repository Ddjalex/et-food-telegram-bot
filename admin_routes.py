from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import AdminUser, AdminActivity, AdminSession, Restaurant, MenuItem, Category, Driver, Order, MenuItemModification
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return redirect(url_for('admin_login'))
        
        admin = AdminUser.query.get(session['admin_user_id'])
        if not admin or not admin.is_active or admin.is_blocked:
            session.clear()
            return redirect(url_for('admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return redirect(url_for('admin_login'))
        
        admin = AdminUser.query.get(session['admin_user_id'])
        if not admin or admin.role != 'super_admin' or not admin.is_active or admin.is_blocked:
            session.clear()
            return redirect(url_for('admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        admin = AdminUser.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            if admin.is_blocked:
                return jsonify({'success': False, 'message': 'Account is blocked'}), 403
            
            if not admin.is_active:
                return jsonify({'success': False, 'message': 'Account is deactivated'}), 403
            
            session['admin_user_id'] = admin.id
            session['admin_role'] = admin.role
            
            # Log session
            admin_session = AdminSession(
                admin_id=admin.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(admin_session)
            
            # Update last login
            admin.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log activity
            log_admin_activity(admin.id, 'login', 'session', description='Admin logged in')
            
            return jsonify({'success': True, 'role': admin.role})
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@admin_required
def admin_logout():
    """Admin logout"""
    admin_id = session.get('admin_user_id')
    if admin_id:
        # Update session end time
        admin_session = AdminSession.query.filter_by(
            admin_id=admin_id,
            logout_time=None
        ).order_by(AdminSession.login_time.desc()).first()
        
        if admin_session:
            admin_session.logout_time = datetime.utcnow()
            admin_session.session_duration = int(
                (admin_session.logout_time - admin_session.login_time).total_seconds() / 60
            )
            db.session.commit()
        
        log_admin_activity(admin_id, 'logout', 'session', description='Admin logged out')
    
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard - different views based on role"""
    admin = AdminUser.query.get(session['admin_user_id'])
    
    if admin.role == 'super_admin':
        return render_template('super_admin_dashboard.html', admin=admin)
    elif admin.role == 'admin':
        return render_template('restaurant_admin_dashboard.html', admin=admin)
    elif admin.role == 'kitchen_staff':
        return render_template('kitchen_staff_dashboard.html', admin=admin)
    
    return redirect(url_for('admin_login'))

# Restaurant Admin API Routes
@app.route('/api/admin/dashboard-stats', methods=['GET'])
@admin_required
def get_admin_dashboard_stats():
    """Get dashboard statistics for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        # Get orders for this admin's restaurant
        from models import Order
        today = datetime.utcnow().date()
        
        orders_query = Order.query.filter_by(restaurant_id=admin.restaurant_id)
        today_orders = orders_query.filter(func.date(Order.created_at) == today).count()
        pending_orders = orders_query.filter_by(status='pending').count()
        
        # Get menu items count
        menu_items = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id).count()
        
        # Calculate today's revenue
        today_revenue = db.session.query(
            func.sum(Order.total_amount)
        ).filter(
            Order.restaurant_id == admin.restaurant_id,
            func.date(Order.created_at) == today
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'todayOrders': today_orders,
            'menuItems': menu_items,
            'todayRevenue': float(today_revenue),
            'pendingOrders': pending_orders
        })
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/recent-orders', methods=['GET'])
@admin_required
def get_recent_orders():
    """Get recent orders for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        from models import Order
        recent_orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id
        ).order_by(Order.created_at.desc()).limit(10).all()
        
        orders_data = []
        for order in recent_orders:
            orders_data.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'status': order.status,
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.isoformat()
            })
        
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Error getting recent orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/popular-items', methods=['GET'])
@admin_required
def get_popular_items():
    """Get popular menu items for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        menu_items = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id).limit(5).all()
        
        items_data = []
        for item in menu_items:
            items_data.append({
                'name': item.name,
                'category': item.category if item.category else 'No Category',
                'order_count': 0,
                'revenue': 0
            })
        
        return jsonify(items_data)
    except Exception as e:
        logger.error(f"Error getting popular items: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/orders', methods=['GET'])
@admin_required
def get_restaurant_admin_orders():
    """Get all orders for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        from models import Order
        orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            # Parse items if they're stored as JSON string
            items = order.items
            if isinstance(items, str):
                try:
                    import json
                    items = json.loads(items)
                except:
                    items = []
            
            orders_data.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat(),
                'items': items
            })
        
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/menu-items', methods=['GET'])
@admin_required
def get_restaurant_menu_items():
    """Get menu items for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        menu_items = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id).all()
        
        items_data = []
        for item in menu_items:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'description': item.description,
                'price': float(item.price),
                'image_url': item.image_url,
                'category_name': item.category.name if item.category else 'No Category',
                'is_available': item.is_available
            })
        
        return jsonify(items_data)
    except Exception as e:
        logger.error(f"Error getting menu items: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/categories', methods=['GET'])
@admin_required
def get_restaurant_categories():
    """Get categories for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        categories = Category.query.filter_by(restaurant_id=admin.restaurant_id).all()
        
        categories_data = []
        for category in categories:
            # Count items in this category
            item_count = MenuItem.query.filter_by(
                category_id=category.id,
                restaurant_id=admin.restaurant_id
            ).count()
            
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'icon': category.icon,
                'item_count': item_count
            })
        
        return jsonify(categories_data)
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/kitchen-stats', methods=['GET'])
@admin_required
def get_kitchen_stats():
    """Get kitchen statistics for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        from models import Order
        preparing_count = Order.query.filter_by(
            restaurant_id=admin.restaurant_id,
            status='preparing'
        ).count()
        
        ready_count = Order.query.filter_by(
            restaurant_id=admin.restaurant_id,
            status='ready'
        ).count()
        
        return jsonify({
            'preparing': preparing_count,
            'ready': ready_count
        })
    except Exception as e:
        logger.error(f"Error getting kitchen stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/drivers', methods=['GET'])
@admin_required
def get_restaurant_drivers():
    """Get drivers for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        from models import Driver
        # Get all drivers since they don't have restaurant_id field
        drivers = Driver.query.all()
        
        drivers_data = []
        for driver in drivers:
            drivers_data.append({
                'id': driver.id,
                'full_name': driver.name,  # Driver model uses 'name' not 'full_name'
                'phone': driver.phone_number,  # Driver model uses 'phone_number' not 'phone'
                'vehicle_type': driver.vehicle_type,
                'status': driver.approval_status,  # Driver model uses 'approval_status' not 'status'
                'is_active': driver.is_active,
                'is_available': driver.is_available,
                'current_latitude': driver.current_lat,  # Driver model uses 'current_lat' not 'current_latitude'
                'current_longitude': driver.current_lng,  # Driver model uses 'current_lng' not 'current_longitude'
                'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None
            })
        
        return jsonify(drivers_data)
    except Exception as e:
        logger.error(f"Error getting drivers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/drivers', methods=['POST'])
@admin_required
def add_restaurant_driver():
    """Add new driver for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        data = request.get_json()
        
        from models import Driver
        
        # Check if driver with same phone already exists
        existing_driver = Driver.query.filter_by(phone_number=data['phone']).first()
        if existing_driver:
            return jsonify({'success': False, 'message': 'Driver with this phone number already exists'}), 400
        
        driver = Driver(
            name=data['full_name'],  # Driver model uses 'name' not 'full_name'
            phone_number=data['phone'],  # Driver model uses 'phone_number' not 'phone'
            vehicle_type=data['vehicle_type'],
            approval_status='approved' if data.get('auto_approve') else 'pending',
            is_approved=data.get('auto_approve', False),
            is_active=True,
            is_available=True,
            telegram_user_id=data.get('telegram_user_id')
        )
        
        db.session.add(driver)
        db.session.commit()
        
        return jsonify({'success': True, 'driver_id': driver.id})
    except Exception as e:
        logger.error(f"Error adding driver: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/drivers/<int:driver_id>', methods=['DELETE'])
@admin_required
def delete_restaurant_driver(driver_id):
    """Delete driver for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        from models import Driver
        driver = Driver.query.filter_by(id=driver_id).first()
        
        if not driver:
            return jsonify({'success': False, 'message': 'Driver not found'}), 404
        
        db.session.delete(driver)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting driver: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Super Admin Routes
@app.route('/api/super-admin/admins', methods=['GET'])
@super_admin_required
def get_admins():
    """Get all admins with performance metrics"""
    try:
        admins = AdminUser.query.filter(AdminUser.role.in_(['admin', 'kitchen_staff'])).all()
        
        admin_data = []
        for admin in admins:
            # Calculate performance metrics
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            
            # Recent activities
            recent_activities = AdminActivity.query.filter(
                AdminActivity.admin_id == admin.id,
                AdminActivity.created_at >= week_ago
            ).count()
            
            # Active sessions this week
            sessions_this_week = AdminSession.query.filter(
                AdminSession.admin_id == admin.id,
                AdminSession.login_time >= week_ago
            ).count()
            
            # Average session duration
            avg_session = db.session.query(
                db.func.avg(AdminSession.session_duration)
            ).filter(
                AdminSession.admin_id == admin.id,
                AdminSession.session_duration.isnot(None)
            ).scalar()
            
            # Get restaurant name if admin has restaurant_id
            restaurant_name = None
            if admin.restaurant_id:
                from models import Restaurant
                restaurant = Restaurant.query.get(admin.restaurant_id)
                restaurant_name = restaurant.name if restaurant else None
            
            admin_info = admin.to_dict()
            admin_info.update({
                'recent_activities': recent_activities,
                'sessions_this_week': sessions_this_week,
                'avg_session_duration': round(avg_session or 0, 2),
                'restaurant_name': restaurant_name
            })
            
            admin_data.append(admin_info)
        
        return jsonify({
            'success': True,
            'admins': admin_data
        })
    except Exception as e:
        logger.error(f"Error fetching admins: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/admins', methods=['POST'])
@super_admin_required
def create_admin():
    """Create new admin"""
    try:
        data = request.get_json()
        
        # Check if username already exists
        if AdminUser.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        # Check if email already exists
        if data.get('email') and AdminUser.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Generate password hash
        password_hash = generate_password_hash(data['password'])
        
        # Create admin
        admin = AdminUser(
            username=data['username'],
            email=data.get('email'),
            full_name=data.get('full_name'),
            phone=data.get('phone'),
            role=data.get('role', 'admin'),
            password_hash=password_hash,
            restaurant_id=data.get('restaurant_id'),
            created_by=session['admin_user_id'],
            permissions=data.get('permissions', {})
        )
        
        db.session.add(admin)
        db.session.commit()
        
        # Log activity
        log_admin_activity(
            session['admin_user_id'],
            'admin_created',
            'admin',
            admin.id,
            f'Created admin: {admin.username}'
        )
        
        return jsonify({
            'success': True,
            'admin': admin.to_dict(),
            'message': 'Admin created successfully'
        })
    
    except Exception as e:
        logger.error(f"Error creating admin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/admins/<int:admin_id>', methods=['PUT'])
@super_admin_required
def update_admin(admin_id):
    """Update admin details"""
    try:
        admin = AdminUser.query.get_or_404(admin_id)
        data = request.get_json()
        
        # Update fields
        if 'full_name' in data:
            admin.full_name = data['full_name']
        if 'email' in data:
            admin.email = data['email']
        if 'phone' in data:
            admin.phone = data['phone']
        if 'restaurant_id' in data:
            admin.restaurant_id = data['restaurant_id']
        if 'permissions' in data:
            admin.permissions = data['permissions']
        
        admin.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log activity
        log_admin_activity(
            session['admin_user_id'],
            'admin_updated',
            'admin',
            admin.id,
            f'Updated admin: {admin.username}'
        )
        
        return jsonify({
            'success': True,
            'admin': admin.to_dict(),
            'message': 'Admin updated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error updating admin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/admins/<int:admin_id>/block', methods=['POST'])
@super_admin_required
def block_admin(admin_id):
    """Block/unblock admin"""
    try:
        admin = AdminUser.query.get_or_404(admin_id)
        data = request.get_json()
        
        admin.is_blocked = data.get('blocked', True)
        admin.updated_at = datetime.utcnow()
        db.session.commit()
        
        action = 'blocked' if admin.is_blocked else 'unblocked'
        log_admin_activity(
            session['admin_user_id'],
            'admin_blocked' if admin.is_blocked else 'admin_unblocked',
            'admin',
            admin.id,
            f'Admin {action}: {admin.username}'
        )
        
        return jsonify({
            'success': True,
            'message': f'Admin {action} successfully'
        })
    
    except Exception as e:
        logger.error(f"Error blocking admin: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/admins/<int:admin_id>/reset-password', methods=['POST'])
@super_admin_required
def reset_admin_password(admin_id):
    """Reset admin password"""
    try:
        admin = AdminUser.query.get_or_404(admin_id)
        data = request.get_json()
        
        new_password = data.get('password')
        if not new_password:
            return jsonify({'success': False, 'message': 'Password required'}), 400
        
        admin.password_hash = generate_password_hash(new_password)
        admin.updated_at = datetime.utcnow()
        db.session.commit()
        
        log_admin_activity(
            session['admin_user_id'],
            'password_reset',
            'admin',
            admin.id,
            f'Password reset for admin: {admin.username}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        })
    
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/admins/<int:admin_id>/performance', methods=['GET'])
@super_admin_required
def get_admin_performance(admin_id):
    """Get detailed admin performance metrics"""
    try:
        admin = AdminUser.query.get_or_404(admin_id)
        
        # Get performance data for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Activities by type
        activity_counts = db.session.query(
            AdminActivity.action_type,
            db.func.count(AdminActivity.id)
        ).filter(
            AdminActivity.admin_id == admin_id,
            AdminActivity.created_at >= thirty_days_ago
        ).group_by(AdminActivity.action_type).all()
        
        # Daily activity chart data
        daily_activities = db.session.query(
            db.func.date(AdminActivity.created_at),
            db.func.count(AdminActivity.id)
        ).filter(
            AdminActivity.admin_id == admin_id,
            AdminActivity.created_at >= thirty_days_ago
        ).group_by(db.func.date(AdminActivity.created_at)).all()
        
        # Session data
        sessions = AdminSession.query.filter(
            AdminSession.admin_id == admin_id,
            AdminSession.login_time >= thirty_days_ago
        ).order_by(AdminSession.login_time.desc()).limit(10).all()
        
        # Response time analysis
        avg_response_time = db.session.query(
            db.func.avg(AdminActivity.response_time)
        ).filter(
            AdminActivity.admin_id == admin_id,
            AdminActivity.response_time.isnot(None)
        ).scalar()
        
        return jsonify({
            'success': True,
            'admin': admin.to_dict(),
            'activity_counts': dict(activity_counts),
            'daily_activities': [{'date': str(date), 'count': count} for date, count in daily_activities],
            'recent_sessions': [session.to_dict() for session in sessions],
            'avg_response_time': round(avg_response_time or 0, 2)
        })
    
    except Exception as e:
        logger.error(f"Error fetching admin performance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Menu Management Routes
@app.route('/api/admin/menu/categories', methods=['GET'])
@admin_required
def get_admin_menu_categories():
    """Get categories for admin's restaurant"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        if admin.role == 'super_admin':
            # Super admin can see all categories
            categories = Category.query.all()
        else:
            # Regular admin sees only their restaurant's categories
            categories = Category.query.filter_by(restaurant_id=admin.restaurant_id).all()
        
        return jsonify({
            'success': True,
            'categories': [category.to_dict() for category in categories]
        })
    
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/menu/categories', methods=['POST'])
@admin_required
def create_admin_category():
    """Create new category"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        data = request.get_json()
        
        restaurant_id = data.get('restaurant_id') or admin.restaurant_id
        
        # Check permission
        if admin.role != 'super_admin' and restaurant_id != admin.restaurant_id:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        category = Category(
            name=data['name'],
            description=data.get('description'),
            icon=data.get('icon', '🍽️'),
            image_url=data.get('image_url'),
            restaurant_id=restaurant_id,
            created_by=admin.id,
            sort_order=data.get('sort_order', 0)
        )
        
        db.session.add(category)
        db.session.commit()
        
        # Log activity
        log_admin_activity(
            admin.id,
            'category_created',
            'category',
            category.id,
            f'Created category: {category.name}'
        )
        
        return jsonify({
            'success': True,
            'category': category.to_dict(),
            'message': 'Category created successfully'
        })
    
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/menu/items', methods=['GET'])
@admin_required
def get_admin_menu_items():
    """Get menu items for admin's restaurant"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        
        if admin.role == 'super_admin':
            # Super admin can see all items
            items = MenuItem.query.all()
        else:
            # Regular admin sees only their restaurant's items
            items = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id).all()
        
        return jsonify({
            'success': True,
            'items': [item.to_dict() for item in items]
        })
    
    except Exception as e:
        logger.error(f"Error fetching menu items: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/menu/items', methods=['POST'])
@admin_required
def create_admin_menu_item():
    """Create new menu item"""
    try:
        admin = AdminUser.query.get(session['admin_user_id'])
        data = request.get_json()
        
        restaurant_id = data.get('restaurant_id') or admin.restaurant_id
        
        # Check permission
        if admin.role != 'super_admin' and restaurant_id != admin.restaurant_id:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        item = MenuItem(
            name=data['name'],
            price=data['price'],
            description=data.get('description'),
            image_url=data.get('image_url'),
            category=data.get('category'),
            restaurant_id=restaurant_id
        )
        
        db.session.add(item)
        db.session.commit()
        
        # Log modification
        modification = MenuItemModification(
            menu_item_id=item.id,
            admin_id=admin.id,
            action='created',
            new_values=item.to_dict()
        )
        db.session.add(modification)
        db.session.commit()
        
        # Log activity
        log_admin_activity(
            admin.id,
            'menu_item_created',
            'menu_item',
            item.id,
            f'Created menu item: {item.name}'
        )
        
        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'message': 'Menu item created successfully'
        })
    
    except Exception as e:
        logger.error(f"Error creating menu item: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper function to log admin activities
def log_admin_activity(admin_id, action_type, entity_type=None, entity_id=None, description=None, response_time=None):
    """Log admin activity for performance tracking"""
    try:
        activity = AdminActivity(
            admin_id=admin_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            response_time=response_time
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

# Additional API endpoints for super admin dashboard
@app.route('/api/super-admin/dashboard-stats', methods=['GET'])
@super_admin_required
def get_dashboard_stats():
    """Get dashboard statistics for super admin"""
    try:
        # Count total admins (excluding super admin)
        total_admins = AdminUser.query.filter(AdminUser.role != 'super_admin').count()
        
        # Count active restaurants
        total_restaurants = Restaurant.query.filter_by(is_active=True).count()
        
        # Count today's orders
        today = datetime.utcnow().date()
        today_orders = Order.query.filter(
            func.date(Order.created_at) == today
        ).count()
        
        # Calculate total revenue
        total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
            Order.status == 'delivered'
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'totalAdmins': total_admins,
            'totalRestaurants': total_restaurants,
            'todayOrders': today_orders,
            'totalRevenue': float(total_revenue)
        })
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/overview', methods=['GET'])
@super_admin_required
def get_overview_data():
    """Get overview data for charts"""
    try:
        # Get admin activity data for charts
        activity_data = db.session.query(
            func.date(AdminActivity.created_at),
            func.count(AdminActivity.id)
        ).group_by(func.date(AdminActivity.created_at)).limit(30).all()
        
        # Get performance distribution
        performance_data = {
            'excellent': 0,
            'good': 0,
            'average': 0,
            'poor': 0
        }
        
        admins = AdminUser.query.filter(AdminUser.role != 'super_admin').all()
        for admin in admins:
            avg_response = db.session.query(
                func.avg(AdminActivity.response_time)
            ).filter(AdminActivity.admin_id == admin.id).scalar() or 0
            
            if avg_response < 5:
                performance_data['excellent'] += 1
            elif avg_response < 15:
                performance_data['good'] += 1
            elif avg_response < 30:
                performance_data['average'] += 1
            else:
                performance_data['poor'] += 1
        
        return jsonify({
            'success': True,
            'activity_data': [{'date': str(date), 'count': count} for date, count in activity_data],
            'performance_data': performance_data
        })
    except Exception as e:
        logger.error(f"Error fetching overview data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/restaurants', methods=['GET'])
@super_admin_required
def get_all_restaurants():
    """Get all restaurants for super admin"""
    try:
        restaurants = Restaurant.query.all()
        
        return jsonify({
            'success': True,
            'restaurants': [restaurant.to_dict() for restaurant in restaurants]
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500