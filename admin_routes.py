from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import AdminUser, AdminActivity, AdminSession, Restaurant, MenuItem, Category, Driver, Order, MenuItemModification
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            # Log the session debug info
            logger.warning(f"Admin authentication failed - no admin_id in session. Session keys: {list(session.keys())}")
            # Check if this is an API request
            if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Authentication required', 'redirect': '/admin/login'}), 401
            return redirect(url_for('admin_login'))
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or not admin.is_active or admin.is_blocked:
            session.clear()
            # Check if this is an API request
            if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Account not active or blocked', 'redirect': '/admin/login'}), 401
            return redirect(url_for('admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('superadmin_login'))
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or admin.role != 'super_admin' or not admin.is_active or admin.is_blocked:
            session.clear()
            return redirect(url_for('superadmin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page (legacy)"""
    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        admin = AdminUser.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            if admin.is_blocked:
                return jsonify({'success': False, 'message': 'Account is blocked'}), 403
            
            if not admin.is_active:
                return jsonify({'success': False, 'message': 'Account is deactivated'}), 403
            
            session['admin_id'] = admin.id
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
            
            # Return JSON for AJAX requests, redirect for form submissions
            if request.is_json:
                return jsonify({'success': True, 'role': admin.role})
            else:
                # Form submission - redirect to dashboard
                if admin.role == 'super_admin':
                    return redirect(url_for('superadmin_dashboard'))
                else:
                    return redirect('/admin')
        
        # Handle error response
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/superadmin/login', methods=['GET', 'POST'])
def superadmin_login():
    """Super Admin login page"""
    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        admin = AdminUser.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            if admin.is_blocked:
                return jsonify({'success': False, 'message': 'Account is blocked'}), 403
            
            if not admin.is_active:
                return jsonify({'success': False, 'message': 'Account is deactivated'}), 403
            
            # Check if user is super admin
            if admin.role != 'super_admin':
                return jsonify({'success': False, 'message': 'No super admin access permissions'}), 403
            
            session['admin_id'] = admin.id
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
            
            # Return JSON for AJAX requests, redirect for form submissions
            if request.is_json:
                return jsonify({'success': True, 'role': admin.role, 'redirect': '/superadmin'})
            else:
                return redirect('/superadmin')
        
        # Handle error response
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        else:
            return render_template('superadmin_login.html', error='Invalid credentials')
    
    return render_template('superadmin_login.html')

@app.route('/superadmin')
@super_admin_required
def superadmin_dashboard():
    """Super Admin dashboard"""
    admin = AdminUser.query.get(session['admin_id'])
    return render_template('super_admin_dashboard.html', admin=admin)

@app.route('/admin/logout')
@admin_required
def admin_logout():
    """Admin logout"""
    admin_id = session.get('admin_id')
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
    return redirect(url_for('admin'))

@app.route('/admin/dashboard-legacy')
@admin_required
def admin_dashboard():
    """Admin dashboard - different views based on role"""
    admin = AdminUser.query.options(db.joinedload(AdminUser.restaurant)).get(session['admin_id'])
    
    if admin.role == 'super_admin':
        return render_template('super_admin_dashboard.html', admin=admin)
    elif admin.role == 'admin':
        return render_template('restaurant_admin_dashboard.html', admin=admin)
    elif admin.role == 'kitchen_staff':
        return render_template('kitchen_dashboard.html', admin=admin)
    
    return redirect(url_for('admin'))

# Restaurant Admin API Routes
@app.route('/api/admin/dashboard-stats', methods=['GET'])
@admin_required
def get_admin_dashboard_stats():
    """Get dashboard statistics for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
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
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
            
        logger.info(f"Getting recent orders for admin {admin.username} (ID: {admin.id}, Restaurant: {admin.restaurant_id})")
        
        from models import Order
        recent_orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id
        ).order_by(Order.created_at.desc()).limit(10).all()
        
        logger.info(f"Found {len(recent_orders)} recent orders for restaurant {admin.restaurant_id}")
        
        orders_data = []
        for order in recent_orders:
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
                'status': order.status,
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.isoformat(),
                'items': items
            })
        
        logger.info(f"Returning {len(orders_data)} recent orders to admin dashboard")
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Error getting recent orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/popular-items', methods=['GET'])
@admin_required
def get_popular_items():
    """Get popular menu items for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
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
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
            
        logger.info(f"Getting orders for admin {admin.username} (ID: {admin.id}, Restaurant: {admin.restaurant_id})")
        
        from models import Order
        orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id
        ).order_by(Order.created_at.desc()).all()
        
        logger.info(f"Found {len(orders)} orders for restaurant {admin.restaurant_id}")
        
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
            
            # Calculate minutes ago for time display
            minutes_ago = int((datetime.utcnow() - order.created_at).total_seconds() / 60)
            
            orders_data.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'customer_address': order.customer_address,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'payment_method': order.payment_method,
                'transaction_id': order.transaction_id,
                'transaction_image_url': order.transaction_image_url,
                'created_at': order.created_at.isoformat(),
                'minutes_ago': minutes_ago,
                'items': items
            })
        
        logger.info(f"Returning {len(orders_data)} orders to admin dashboard")
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/menu-items', methods=['GET'])
@admin_required
def get_restaurant_menu_items():
    """Get menu items for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
            
        logger.info(f"Getting menu items for admin {admin.username} (ID: {admin.id}, Restaurant: {admin.restaurant_id})")
        
        menu_items = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id).all()
        logger.info(f"Found {len(menu_items)} menu items for restaurant {admin.restaurant_id}")
        
        items_data = []
        for item in menu_items:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'description': item.description,
                'price': float(item.price),
                'image_url': item.image_url,
                'category_name': item.category if isinstance(item.category, str) else 'No Category',
                'is_available': item.available
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
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        # Get unique categories from menu items
        from sqlalchemy import distinct
        categories = db.session.query(distinct(MenuItem.category)).filter_by(restaurant_id=admin.restaurant_id).all()
        
        categories_data = []
        for i, (category_name,) in enumerate(categories):
            # Skip None categories
            if not category_name:
                continue
                
            # Count items in this category
            item_count = MenuItem.query.filter_by(
                category=category_name,
                restaurant_id=admin.restaurant_id
            ).count()
            
            categories_data.append({
                'id': i + 1,
                'name': category_name,
                'description': f'{category_name} category',
                'icon': '🍔' if 'burger' in category_name.lower() else '🍕',
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
        admin = AdminUser.query.get(session['admin_id'])
        
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
def get_restaurant_drivers():
    """Get drivers for restaurant admin with real-time location status"""
    try:
        # Check authentication
        if 'admin_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
            
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
            
        from models import Driver
        from datetime import datetime, timedelta
        
        # Get drivers based on admin role and driver availability status
        if admin.role == 'super_admin':
            # Super admin sees all drivers
            drivers = Driver.query.all()
        else:
            # Regular restaurant admin sees:
            # 1. Their own restaurant's drivers (regardless of status)
            # 2. Available drivers from other restaurants (not busy)
            own_drivers = Driver.query.filter_by(restaurant_id=admin.restaurant_id).all()
            available_other_drivers = Driver.query.filter(
                Driver.restaurant_id != admin.restaurant_id,
                Driver.is_available == True,
                Driver.approval_status == 'approved'
            ).all()
            drivers = own_drivers + available_other_drivers
        
        logger.info(f"Getting drivers for admin {admin.username} (ID: {admin.id}, Restaurant: {admin.restaurant_id}, Role: {admin.role})")
        logger.info(f"Found {len(drivers)} drivers")
        
        drivers_data = []
        for driver in drivers:
            # Enhanced location status calculation
            location_status = 'inactive'
            last_update_text = "Never"
            minutes_ago = None
            
            if hasattr(driver, 'last_location_update') and driver.last_location_update:
                time_diff = datetime.utcnow() - driver.last_location_update
                minutes_ago = time_diff.total_seconds() / 60
                
                if minutes_ago < 2:
                    location_status = 'live'
                    last_update_text = "Live (now)"
                elif minutes_ago < 10:
                    location_status = 'active'
                    last_update_text = f"{int(minutes_ago)} minutes ago"
                elif minutes_ago < 60:
                    location_status = 'recent'
                    last_update_text = f"{int(minutes_ago)} minutes ago"
                else:
                    location_status = 'inactive'
                    hours_ago = minutes_ago / 60
                    if hours_ago < 24:
                        last_update_text = f"{int(hours_ago)} hours ago"
                    else:
                        days_ago = hours_ago / 24
                        last_update_text = f"{int(days_ago)} days ago"
            
            # Determine driver availability display
            availability_status = "AVAILABLE" if driver.is_available else "BUSY"
            availability_class = "text-success" if driver.is_available else "text-warning"
            
            driver_data = {
                'id': driver.id,
                'full_name': driver.name,
                'phone': driver.phone_number,
                'vehicle_type': driver.vehicle_type or 'Unknown',
                'status': driver.approval_status or 'pending',
                'is_active': driver.is_active,
                'is_available': driver.is_available,
                'availability_status': availability_status,
                'availability_class': availability_class,
                'location_status': location_status,
                'last_update_text': last_update_text,
                'minutes_ago': int(minutes_ago) if minutes_ago else None,
                'telegram_user_id': driver.telegram_user_id,
                'restaurant_id': driver.restaurant_id
            }
            
            # Add location data if available
            if hasattr(driver, 'current_lat') and hasattr(driver, 'current_lng'):
                driver_data['current_latitude'] = driver.current_lat
                driver_data['current_longitude'] = driver.current_lng
                
            if hasattr(driver, 'last_location_update'):
                driver_data['last_location_update'] = driver.last_location_update.isoformat() if driver.last_location_update else None
            
            drivers_data.append(driver_data)
        
        return jsonify(drivers_data)
    except Exception as e:
        logger.error(f"Error getting drivers: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/drivers', methods=['POST'])
def add_restaurant_driver():
    """Add new driver for restaurant admin"""
    try:
        # Check authentication
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'success': False, 'error': 'Admin not found'}), 404
            
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
            telegram_user_id=data.get('telegram_user_id'),
            restaurant_id=admin.restaurant_id  # Assign driver to the admin's restaurant
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
        admin = AdminUser.query.get(session['admin_id'])
        
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

# Super Admin Driver Management Routes
@app.route('/api/super-admin/drivers/pending', methods=['GET'])
@super_admin_required
def get_super_admin_pending_drivers():
    """Get all pending driver applications for super admin approval"""
    try:
        from admin_approval_system import get_pending_drivers
        pending_drivers = get_pending_drivers()
        
        drivers_data = []
        for driver in pending_drivers:
            driver_data = {
                'id': driver.id,
                'name': driver.name,
                'phone_number': driver.phone_number,
                'telegram_user_id': driver.telegram_user_id,
                'vehicle_type': driver.vehicle_type,
                'approval_status': driver.approval_status,
                'created_at': driver.created_at.isoformat() if driver.created_at else None,
                'license_document': driver.license_document,
                'id_document': driver.id_document,
                'vehicle_document': driver.vehicle_document,
                'current_lat': driver.current_lat,
                'current_lng': driver.current_lng,
                'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None
            }
            drivers_data.append(driver_data)
        
        return jsonify({
            'success': True,
            'drivers': drivers_data,
            'total_pending': len(drivers_data)
        })
    
    except Exception as e:
        logger.error(f"Error fetching pending drivers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/drivers/<int:driver_id>/approve', methods=['POST'])
@super_admin_required
def approve_driver_super_admin(driver_id):
    """Approve a pending driver application (Super Admin only)"""
    try:
        from admin_approval_system import approve_driver
        from driver_bot import send_driver_message
        
        admin = AdminUser.query.get(session['admin_id'])
        success = approve_driver(driver_id, admin_telegram_id=admin.telegram_user_id)
        
        if success:
            # Send real-time notifications to all restaurant admins
            try:
                from real_time_notifications import notify_restaurants_new_driver
                notify_restaurants_new_driver(driver_id)
            except Exception as notify_error:
                logger.error(f"Error sending driver approval notifications: {notify_error}")
            
            # Log admin activity
            log_admin_activity(
                admin.id,
                'driver_approved',
                'driver',
                driver_id,
                f'Approved driver application ID: {driver_id}'
            )
            
            # Get driver for additional notification
            driver = Driver.query.get(driver_id)
            if driver and driver.telegram_user_id:
                # Send enhanced live location request message
                location_message = f"""📍 *LIVE LOCATION REQUIRED*\n\n"""
                location_message += f"🎯 **{driver.name}**, to start receiving delivery orders, you MUST share your live location.\n\n"""
                location_message += f"🚚 **How to Enable Live Location:**\n"
                location_message += f"1. Click 'Share Location' below\n"
                location_message += f"2. Select 'Live Location' (not just current location)\n"
                location_message += f"3. Set duration to 8 hours\n"
                location_message += f"4. Confirm sharing\n\n"
                location_message += f"⚠️ **Important:** Without live location, you won't receive any delivery orders!\n\n"
                location_message += f"✅ **Once enabled, all restaurants will see you in real-time for order assignments.**"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📍 Share Live Location Now",
                                "callback_data": "request_location"
                            }
                        ],
                        [
                            {
                                "text": "📱 Check Status",
                                "callback_data": "driver_status"
                            },
                            {
                                "text": "❓ Need Help?",
                                "callback_data": "location_help"
                            }
                        ]
                    ]
                }
                
                send_driver_message(driver.telegram_user_id, location_message, keyboard=keyboard)
            
            return jsonify({
                'success': True,
                'message': f'Driver approved successfully and notified about live location requirement'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to approve driver'}), 500
    
    except Exception as e:
        logger.error(f"Error approving driver: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/drivers/stats', methods=['GET'])
@super_admin_required
def get_super_admin_driver_stats():
    """Get driver statistics for super admin dashboard"""
    try:
        from datetime import datetime, timedelta
        
        # Get all drivers
        all_drivers = Driver.query.all()
        total_drivers = len(all_drivers)
        
        # Count drivers by status
        approved_drivers = Driver.query.filter_by(approval_status='approved').count()
        pending_drivers = Driver.query.filter_by(approval_status='pending').count()
        active_drivers = Driver.query.filter_by(is_active=True).count()
        available_drivers = Driver.query.filter_by(is_active=True, is_available=True).count()
        
        # Count drivers with recent location updates (within 10 minutes)
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        online_drivers = Driver.query.filter(
            Driver.is_active == True,
            Driver.last_location_update >= ten_minutes_ago
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total_drivers,
                'approved': approved_drivers,
                'pending': pending_drivers,
                'active': active_drivers,
                'available': available_drivers,
                'online': online_drivers,
                'offline': total_drivers - online_drivers
            }
        })
    
    except Exception as e:
        logger.error(f"Error fetching driver stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/drivers/<int:driver_id>/reject', methods=['POST'])
@super_admin_required
def reject_driver_super_admin(driver_id):
    """Reject a pending driver application (Super Admin only)"""
    try:
        from admin_approval_system import reject_driver
        
        admin = AdminUser.query.get(session['admin_id'])
        data = request.get_json()
        reason = data.get('reason', 'Application does not meet requirements')
        
        success = reject_driver(driver_id, admin_telegram_id=admin.telegram_user_id, reason=reason)
        
        if success:
            # Log admin activity
            log_admin_activity(
                admin.id,
                'driver_rejected',
                'driver',
                driver_id,
                f'Rejected driver application ID: {driver_id} - Reason: {reason}'
            )
            
            return jsonify({
                'success': True,
                'message': f'Driver application rejected and notification sent'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to reject driver'}), 500
    
    except Exception as e:
        logger.error(f"Error rejecting driver: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/drivers/<int:driver_id>/documents', methods=['GET'])
@super_admin_required
def get_driver_documents_super_admin(driver_id):
    """Get driver documents for super admin review"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        # Create array of documents for the frontend
        documents = []
        
        # Driver information
        driver_info = {
            'driver_id': driver.id,
            'driver_name': driver.name,
            'phone_number': driver.phone_number,
            'vehicle_type': driver.vehicle_type,
            'approval_status': driver.approval_status,
            'created_at': driver.created_at.isoformat() if driver.created_at else None
        }
        
        # Add license document if exists
        if driver.license_document:
            documents.append({
                'document_type': 'Driver License',
                'document_url': driver.license_document,
                'file_name': 'License Document'
            })
        
        # Add ID document if exists
        if driver.id_document:
            documents.append({
                'document_type': 'Government ID',
                'document_url': driver.id_document,
                'file_name': 'ID Document'
            })
        
        # Add vehicle document if exists  
        if driver.vehicle_document:
            documents.append({
                'document_type': 'Vehicle Registration',
                'document_url': driver.vehicle_document,
                'file_name': 'Vehicle Registration'
            })
        
        return jsonify({
            'success': True,
            'documents': documents,
            'driver_info': driver_info
        })
    
    except Exception as e:
        logger.error(f"Error fetching driver documents: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/drivers/approved', methods=['GET'])
@super_admin_required
def get_approved_drivers_super_admin():
    """Get all approved drivers with live location status"""
    try:
        from datetime import datetime, timedelta
        
        approved_drivers = Driver.query.filter_by(approval_status='approved').all()
        
        drivers_data = []
        for driver in approved_drivers:
            # Enhanced location status calculation
            location_status = 'inactive'
            last_update_text = "Never"
            minutes_ago = None
            
            if driver.last_location_update:
                time_diff = datetime.utcnow() - driver.last_location_update
                minutes_ago = time_diff.total_seconds() / 60
                
                if minutes_ago < 2:
                    location_status = 'live'
                elif minutes_ago < 10:
                    location_status = 'active'
                elif minutes_ago < 60:
                    location_status = 'recent'
                else:
                    location_status = 'inactive'
                
                if minutes_ago < 60:
                    last_update_text = f"{int(minutes_ago)} minutes ago"
                else:
                    hours_ago = minutes_ago / 60
                    if hours_ago < 24:
                        last_update_text = f"{int(hours_ago)} hours ago"
                    else:
                        days_ago = hours_ago / 24
                        last_update_text = f"{int(days_ago)} days ago"
            
            driver_data = {
                'id': driver.id,
                'name': driver.name,
                'phone_number': driver.phone_number,
                'telegram_user_id': driver.telegram_user_id,
                'vehicle_type': driver.vehicle_type,
                'is_active': driver.is_active,
                'is_available': driver.is_available,
                'current_lat': driver.current_lat,
                'current_lng': driver.current_lng,
                'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
                'location_status': location_status,
                'last_update_text': last_update_text,
                'minutes_ago': int(minutes_ago) if minutes_ago else None,
                'approved_at': driver.approved_at.isoformat() if driver.approved_at else None
            }
            drivers_data.append(driver_data)
        
        return jsonify({
            'success': True,
            'drivers': drivers_data,
            'total_approved': len(drivers_data)
        })
    
    except Exception as e:
        logger.error(f"Error fetching approved drivers: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/real-time-stats', methods=['GET'])
@super_admin_required
def get_real_time_stats():
    """Get real-time system statistics for super admin"""
    try:
        from datetime import datetime, timedelta
        
        # Driver location statistics
        approved_drivers = Driver.query.filter_by(approval_status='approved').all()
        
        total_drivers = len(approved_drivers)
        online_drivers = 0
        live_location_drivers = 0
        available_drivers = 0
        busy_drivers = 0
        
        for driver in approved_drivers:
            if driver.is_active:
                online_drivers += 1
                
                if driver.last_location_update:
                    time_diff = datetime.utcnow() - driver.last_location_update
                    if time_diff < timedelta(minutes=5):
                        live_location_drivers += 1
                
                if driver.is_available:
                    available_drivers += 1
                else:
                    busy_drivers += 1
        
        # Active orders statistics
        from models import Order
        active_orders = Order.query.filter(
            Order.status.in_(['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery'])
        ).count()
        
        # Today's order statistics
        from sqlalchemy import func
        today = datetime.utcnow().date()
        today_orders = Order.query.filter(
            func.date(Order.created_at) == today
        ).count()
        
        # Revenue statistics
        today_revenue = db.session.query(func.sum(Order.total_amount)).filter(
            func.date(Order.created_at) == today,
            Order.status.in_(['delivered', 'confirmed', 'preparing', 'ready', 'out_for_delivery'])
        ).scalar() or 0
        
        # Active restaurants
        active_restaurants = Restaurant.query.filter_by(is_active=True).count()
        
        # Active admins (logged in within last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        # Note: AdminSession model needs to be implemented for proper tracking
        active_admins = AdminUser.query.filter_by(is_active=True).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'drivers': {
                    'total': total_drivers,
                    'online': online_drivers,
                    'live_location': live_location_drivers,
                    'available': available_drivers,
                    'busy': busy_drivers,
                    'offline': total_drivers - online_drivers
                },
                'orders': {
                    'active': active_orders,
                    'today': today_orders,
                    'today_revenue': float(today_revenue)
                },
                'system': {
                    'active_restaurants': active_restaurants,
                    'active_admins': active_admins
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching real-time stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/drivers/<int:driver_id>/request-location', methods=['POST'])
@super_admin_required
def request_driver_location_super_admin(driver_id):
    """Request live location from a specific driver (Super Admin)"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        if not driver.telegram_user_id:
            return jsonify({'success': False, 'message': 'Driver has no Telegram account linked'}), 400
        
        # Import the driver bot function
        from bot_minimal import request_driver_location
        
        # Request location from driver
        success = request_driver_location(driver.telegram_user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Location request sent to {driver.name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send location request'
            }), 500
    except Exception as e:
        logger.error(f"Error requesting driver location: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/system-health', methods=['GET'])
@super_admin_required
def get_system_health():
    """Get real-time system health status"""
    try:
        from datetime import datetime, timedelta
        import os
        
        # Database connectivity check
        db_status = 'healthy'
        try:
            db.session.execute('SELECT 1')
            db_status = 'healthy'
        except Exception as e:
            db_status = 'error'
            logger.error(f"Database health check failed: {e}")
        
        # Bot connectivity check
        bot_status = 'healthy'
        try:
            # Check if bot tokens are configured
            customer_bot_token = os.environ.get('ETFASTFOOD_BOT_TOKEN')
            driver_bot_token = os.environ.get('DRIVER_BOT_TOKEN')
            
            if not customer_bot_token or not driver_bot_token:
                bot_status = 'warning'
        except Exception as e:
            bot_status = 'error'
            logger.error(f"Bot health check failed: {e}")
        
        # Recent error rate
        last_hour = datetime.utcnow() - timedelta(hours=1)
        recent_errors = 0  # This could be enhanced with actual error logging
        
        # Active connections (simplified)
        # Note: AdminSession model needs to be implemented for proper session tracking
        active_sessions = AdminUser.query.filter_by(is_active=True).count()
        
        health_data = {
            'database': {
                'status': db_status,
                'message': 'Database connection is healthy' if db_status == 'healthy' else 'Database connection issues detected'
            },
            'bots': {
                'status': bot_status,
                'message': 'Bot services are operational' if bot_status == 'healthy' else 'Bot configuration issues detected'
            },
            'performance': {
                'active_sessions': active_sessions,
                'recent_errors': recent_errors,
                'status': 'healthy' if recent_errors < 10 else 'warning'
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'health': health_data
        })
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/change-password', methods=['POST'])
@super_admin_required
def change_admin_password():
    """Change admin password"""
    try:
        from werkzeug.security import check_password_hash, generate_password_hash
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'Current password and new password are required'}), 400
        
        # Get current admin
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'success': False, 'message': 'Admin not found'}), 404
        
        # Verify current password
        if not check_password_hash(admin.password_hash, current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
        
        # Validate new password
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'New password must be at least 6 characters long'}), 400
        
        # Update password
        admin.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        # Log activity
        log_admin_activity(
            admin.id,
            'password_changed',
            'admin',
            admin.id,
            'Admin password changed successfully'
        )
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/drivers/<int:driver_id>', methods=['DELETE'])
def delete_driver_super_admin(driver_id):
    """Delete a driver (Super Admin only)"""
    try:
        # Check if user is authenticated as super admin
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or admin.role != 'super_admin':
            return jsonify({'success': False, 'error': 'Super admin access required'}), 403
            
        from models import Driver
        
        driver = Driver.query.get_or_404(driver_id)
        
        # Check if driver has active orders
        active_orders = Order.query.filter_by(driver_id=driver_id, status='out_for_delivery').count()
        
        if active_orders > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete driver. Driver has {active_orders} active orders.'
            }), 400
        
        # Log activity before deletion
        log_admin_activity(
            session['admin_id'],
            'driver_deleted',
            'driver',
            driver_id,
            f'Deleted driver: {driver.name}'
        )
        
        # Delete driver
        db.session.delete(driver)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Driver deleted successfully'
        })
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
            created_by=session['admin_id'],
            permissions=data.get('permissions', {})
        )
        
        db.session.add(admin)
        db.session.commit()
        
        # Log activity
        log_admin_activity(
            session['admin_id'],
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
            session['admin_id'],
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
            session['admin_id'],
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

@app.route('/api/super-admin/admins/<int:admin_id>', methods=['DELETE'])
@super_admin_required
def delete_admin(admin_id):
    """Delete admin (Super Admin only)"""
    try:
        admin = AdminUser.query.get_or_404(admin_id)
        
        if admin.role == 'super_admin':
            return jsonify({'success': False, 'message': 'Cannot delete super admin'}), 400
        
        # Store admin info for response
        admin_name = admin.username
        admin_full_name = admin.full_name
        
        # Check if admin has active sessions and force close them
        active_sessions = AdminSession.query.filter_by(admin_id=admin_id, logout_time=None).all()
        if active_sessions:
            # Force logout all active sessions
            for session_obj in active_sessions:
                session_obj.logout_time = datetime.utcnow()
                session_obj.logout_reason = 'Admin account deleted by super admin'
            db.session.commit()
        
        # Log admin activity before deletion
        log_admin_activity(
            session['admin_id'],
            'admin_deleted',
            'admin',
            admin_id,
            f'Deleted admin: {admin.username} ({admin.full_name}) - Force closed {len(active_sessions)} active sessions'
        )
        
        # Delete related records first
        AdminActivity.query.filter_by(admin_id=admin_id).delete()
        AdminSession.query.filter_by(admin_id=admin_id).delete()
        
        # Delete admin
        db.session.delete(admin)
        db.session.commit()
        
        message = f'Admin "{admin_name}" deleted successfully'
        if active_sessions:
            message += f' (forced logout from {len(active_sessions)} active sessions)'
        
        return jsonify({
            'success': True,
            'message': message
        })
    
    except Exception as e:
        logger.error(f"Error deleting admin: {e}")
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
            session['admin_id'],
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
        admin = AdminUser.query.get(session['admin_id'])
        
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
        admin = AdminUser.query.get(session['admin_id'])
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
        admin = AdminUser.query.get(session['admin_id'])
        
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

@app.route('/api/super-admin/restaurants/<int:restaurant_id>/upload-images', methods=['POST'])
@super_admin_required
def upload_restaurant_images(restaurant_id):
    """Upload logo and cover image for a restaurant"""
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        
        if 'logo' not in request.files and 'cover_image' not in request.files:
            return jsonify({'success': False, 'message': 'No files uploaded'}), 400
        
        uploaded_files = {}
        
        # Handle logo upload
        if 'logo' in request.files:
            logo_file = request.files['logo']
            if logo_file and logo_file.filename:
                if allowed_file(logo_file.filename):
                    # Generate unique filename
                    import time
                    timestamp = str(int(time.time() * 1000))
                    filename = f"{timestamp}_{secure_filename(logo_file.filename)}"
                    
                    # Save file
                    upload_folder = os.path.join('static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    logo_file.save(file_path)
                    
                    # Update restaurant
                    restaurant.logo_url = f'/static/uploads/{filename}'
                    uploaded_files['logo'] = restaurant.logo_url
        
        # Handle cover image upload
        if 'cover_image' in request.files:
            cover_file = request.files['cover_image']
            if cover_file and cover_file.filename:
                if allowed_file(cover_file.filename):
                    # Generate unique filename
                    import time
                    timestamp = str(int(time.time() * 1000))
                    filename = f"{timestamp}_{secure_filename(cover_file.filename)}"
                    
                    # Save file
                    upload_folder = os.path.join('static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    cover_file.save(file_path)
                    
                    # Update restaurant
                    restaurant.cover_image_url = f'/static/uploads/{filename}'
                    uploaded_files['cover_image'] = restaurant.cover_image_url
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Images uploaded successfully',
            'uploaded_files': uploaded_files,
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.name,
                'logo_url': restaurant.logo_url,
                'cover_image_url': restaurant.cover_image_url
            }
        })
        
    except Exception as e:
        logger.error(f"Error uploading restaurant images: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/admin/menu/items', methods=['POST'])
@admin_required
def create_admin_menu_item():
    """Create new menu item"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
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

# Public dashboard stats endpoint for overview
@app.route('/api/dashboard-stats', methods=['GET'])
def get_public_dashboard_stats():
    """Get public dashboard statistics"""
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
        logger.error(f"Error fetching public dashboard stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

# Restaurant-specific overview data endpoint
@app.route('/api/overview-data', methods=['GET'])
@admin_required
def get_restaurant_overview_data():
    """Get restaurant-specific overview data for charts"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
        # Get recent orders for this restaurant only
        recent_orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id
        ).order_by(Order.created_at.desc()).limit(30).all()
        
        # Group by date for revenue chart
        revenue_data = {}
        for order in recent_orders:
            date_str = order.created_at.strftime('%Y-%m-%d')
            if date_str not in revenue_data:
                revenue_data[date_str] = 0
            if order.status == 'delivered':
                revenue_data[date_str] += order.total_amount
        
        # Order status distribution for this restaurant only
        status_data = {
            'pending': Order.query.filter_by(restaurant_id=admin.restaurant_id, status='pending').count(),
            'confirmed': Order.query.filter_by(restaurant_id=admin.restaurant_id, status='confirmed').count(),
            'preparing': Order.query.filter_by(restaurant_id=admin.restaurant_id, status='preparing').count(),
            'ready': Order.query.filter_by(restaurant_id=admin.restaurant_id, status='ready').count(),
            'out_for_delivery': Order.query.filter_by(restaurant_id=admin.restaurant_id, status='out_for_delivery').count(),
            'delivered': Order.query.filter_by(restaurant_id=admin.restaurant_id, status='delivered').count(),
        }
        
        return jsonify({
            'success': True,
            'revenue_data': [{'date': date, 'amount': amount} for date, amount in revenue_data.items()],
            'status_data': status_data
        })
    except Exception as e:
        logger.error(f"Error fetching restaurant overview data: {e}")
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

# Super Admin Restaurant Management Routes
@app.route('/api/super-admin/restaurants', methods=['GET'])
@super_admin_required
def get_all_restaurants():
    """Get all restaurants for super admin"""
    try:
        restaurants = Restaurant.query.all()
        
        restaurants_data = []
        for restaurant in restaurants:
            # Count associated data
            menu_items_count = len(restaurant.menu_items)
            orders_count = Order.query.filter_by(restaurant_id=restaurant.id).count()
            admins_count = AdminUser.query.filter_by(restaurant_id=restaurant.id).count()
            
            restaurant_data = restaurant.to_dict()
            restaurant_data.update({
                'menu_items_count': menu_items_count,
                'orders_count': orders_count,
                'admins_count': admins_count
            })
            restaurants_data.append(restaurant_data)
        
        return jsonify({
            'success': True,
            'restaurants': restaurants_data
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/super-admin/restaurants/<int:restaurant_id>', methods=['DELETE'])
@super_admin_required
def delete_restaurant_super_admin(restaurant_id):
    """Delete a restaurant (Super Admin only)"""
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        
        # Check if restaurant has orders
        orders_count = Order.query.filter_by(restaurant_id=restaurant_id).count()
        if orders_count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete restaurant with {orders_count} orders. Please handle orders first.'
            }), 400
        
        # Check if restaurant has admins
        admins_count = AdminUser.query.filter_by(restaurant_id=restaurant_id).count()
        if admins_count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete restaurant with {admins_count} admin users. Please reassign or remove admins first.'
            }), 400
        
        # Delete associated menu items and categories
        from models import MenuItem, Category
        MenuItem.query.filter_by(restaurant_id=restaurant_id).delete()
        Category.query.filter_by(restaurant_id=restaurant_id).delete()
        
        # Delete the restaurant
        restaurant_name = restaurant.name
        db.session.delete(restaurant)
        db.session.commit()
        
        logger.info(f"Restaurant '{restaurant_name}' (ID: {restaurant_id}) deleted by super admin")
        
        return jsonify({
            'success': True,
            'message': f'Restaurant "{restaurant_name}" deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting restaurant: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/restaurants/super-admin', methods=['POST'])
@super_admin_required  
def create_restaurant():
    """Create new restaurant with image upload support (super admin only)"""
    try:
        # Handle both JSON and FormData
        if request.is_json:
            data = request.get_json()
        else:
            # Handle FormData from file upload
            data = request.form.to_dict()
            # Convert string boolean values
            data['is_active'] = data.get('is_active') == 'on'
            data['is_featured'] = data.get('is_featured') == 'on'
            # Convert numeric values
            try:
                data['latitude'] = float(data.get('latitude', 9.047658))
                data['longitude'] = float(data.get('longitude', 38.741143))
                data['delivery_fee'] = float(data.get('delivery_fee', 50.0))
                data['minimum_order'] = float(data.get('minimum_order', 100.0))
            except (ValueError, TypeError):
                data['latitude'] = 9.047658
                data['longitude'] = 38.741143
                data['delivery_fee'] = 50.0
                data['minimum_order'] = 100.0
        
        # Validation
        required_fields = ['name', 'address', 'phone']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Check if restaurant name already exists
        existing_restaurant = Restaurant.query.filter_by(name=data['name']).first()
        if existing_restaurant:
            return jsonify({'success': False, 'message': 'Restaurant name already exists'}), 400
        
        # Create restaurant
        restaurant = Restaurant(
            name=data['name'],
            address=data['address'],
            phone=data['phone'],
            latitude=data.get('latitude', 9.0),
            longitude=data.get('longitude', 38.0),
            delivery_fee=data.get('delivery_fee', 50.0),
            minimum_order=data.get('minimum_order', 100.0),
            estimated_delivery_time=data.get('estimated_delivery_time', '30-45 minutes'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            is_featured=data.get('is_featured', False)
        )
        
        db.session.add(restaurant)
        db.session.flush()  # Get restaurant ID without committing
        
        # Auto-create restaurant admin and kitchen staff
        restaurant_name_clean = data['name'].replace(' ', '').replace('|', '').lower()
        
        # Create restaurant admin
        admin_username = f"{restaurant_name_clean}_admin"
        admin = AdminUser(
            username=admin_username,
            full_name=f"{data['name']} Administrator",
            phone=data.get('admin_phone', data['phone']),
            role='admin',
            password_hash=generate_password_hash(f"{restaurant_name_clean}123"),
            restaurant_id=restaurant.id,
            is_active=True
        )
        db.session.add(admin)
        
        # Create kitchen staff for the restaurant
        kitchen_username = f"{restaurant_name_clean}_kitchen"
        kitchen_staff = AdminUser(
            username=kitchen_username,
            full_name=f"{data['name']} Kitchen Team",
            phone=data.get('kitchen_phone', data['phone']),
            role='kitchen_staff',
            password_hash=generate_password_hash(f"{restaurant_name_clean}kitchen123"),
            restaurant_id=restaurant.id,
            is_active=True,
            telegram_user_id=None  # Will be set when they start the bot
        )
        db.session.add(kitchen_staff)
        
        # Handle image uploads if present in form data
        uploaded_files = {}
        if not request.is_json and request.files:
            # Handle logo upload
            if 'logo' in request.files:
                logo_file = request.files['logo']
                if logo_file and logo_file.filename and allowed_file(logo_file.filename):
                    # Generate unique filename
                    import time
                    timestamp = str(int(time.time() * 1000))
                    filename = f"{timestamp}_{secure_filename(logo_file.filename)}"
                    
                    # Save file
                    upload_folder = os.path.join('static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    logo_file.save(file_path)
                    
                    # Update restaurant logo URL
                    restaurant.logo_url = f'/static/uploads/{filename}'
                    uploaded_files['logo'] = restaurant.logo_url
            
            # Handle cover image upload
            if 'cover_image' in request.files:
                cover_file = request.files['cover_image']
                if cover_file and cover_file.filename and allowed_file(cover_file.filename):
                    # Generate unique filename
                    import time
                    timestamp = str(int(time.time() * 1000))
                    filename = f"{timestamp}_{secure_filename(cover_file.filename)}"
                    
                    # Save file
                    upload_folder = os.path.join('static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    cover_file.save(file_path)
                    
                    # Update restaurant cover image URL
                    restaurant.cover_image_url = f'/static/uploads/{filename}'
                    uploaded_files['cover_image'] = restaurant.cover_image_url
        
        db.session.commit()
        
        # Log activity
        log_admin_activity(
            session['admin_id'],
            'restaurant_created',
            'restaurant',
            restaurant.id,
            f'Created restaurant: {restaurant.name}' + (f' with {len(uploaded_files)} image(s)' if uploaded_files else '')
        )
        
        message = 'Restaurant created successfully'
        if uploaded_files:
            message += f' with {len(uploaded_files)} image(s) uploaded'
        
        return jsonify({
            'success': True,
            'restaurant': restaurant.to_dict(),
            'uploaded_files': uploaded_files,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error creating restaurant: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/payment-notifications', methods=['GET'])
@admin_required
def get_admin_payment_notifications():
    """Get payment verification orders for admin dashboard"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
        from models import Order
        # Get orders that need payment verification (with or without payment images)
        orders = Order.query.filter(
            Order.restaurant_id == admin.restaurant_id,
            Order.status.in_(['pending', 'confirmed']),
            Order.payment_verified_at.is_(None)  # Not yet verified
        ).order_by(Order.created_at.desc()).all()
        
        notifications = []
        for order in orders:
            notifications.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'customer_phone': getattr(order, 'customer_phone', 'N/A'),
                'total_amount': order.total_amount,
                'payment_method': order.payment_method or 'Manual verification required',
                'transaction_id': order.transaction_id or 'N/A',
                'transaction_image_url': order.transaction_image_url,
                'created_at': order.created_at.isoformat(),
                'status': order.status
            })
        
        return jsonify({
            'success': True,
            'notifications': notifications
        })
    except Exception as e:
        logger.error(f"Error loading payment notifications: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/verify-payment/<int:order_id>', methods=['POST'])
@admin_required
def verify_payment_admin(order_id):
    """Verify payment for an order (admin, super_admin, or kitchen_staff)"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
        # Check if user has permission to verify payments
        if admin.role not in ['admin', 'super_admin', 'kitchen_staff']:
            return jsonify({'success': False, 'message': 'Insufficient permissions to verify payments'}), 403
        
        from models import Order, KitchenStaff
        order = Order.query.filter_by(id=order_id, restaurant_id=admin.restaurant_id).first()
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        # Check if order is already verified
        if order.payment_verified_at:
            return jsonify({'success': False, 'message': 'Payment already verified'}), 400
        
        # Update order status to confirmed
        old_status = order.status
        order.status = 'confirmed'
        order.payment_verified_at = datetime.utcnow()
        
        # If no payment method specified, mark as cash/manual verification
        if not order.payment_method:
            order.payment_method = 'Manual verification'
            
        db.session.commit()
        
        # Log activity
        log_admin_activity(admin.id, 'payment_verified', 'order', order_id, f'Payment verified for order #{order_id}')
        
        # Send real-time notification about order status change
        try:
            from real_time_notifications import notify_order_status_change
            notify_order_status_change(order_id, 'confirmed', admin_action=True)
        except Exception as notify_error:
            logger.error(f"Error sending order status notification: {notify_error}")
        
        # Send notification to kitchen staff
        try:
            from payment_workflow import notify_kitchen_staff_payment_verified
            notify_kitchen_staff_payment_verified(order)
        except Exception as notify_error:
            logger.error(f"Error notifying kitchen staff: {notify_error}")
        
        # Send notification to customer
        try:
            from payment_workflow import notify_customer_payment_approved
            notify_customer_payment_approved(order)
        except Exception as customer_error:
            logger.error(f"Error notifying customer: {customer_error}")
        
        return jsonify({'success': True, 'message': 'Payment verified successfully'})
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/reject-payment/<int:order_id>', methods=['POST'])
@admin_required
def reject_payment_admin(order_id):
    """Reject payment for an order (admin only)"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        data = request.get_json()
        reason = data.get('reason', 'Payment rejected')
        
        from models import Order
        order = Order.query.filter_by(id=order_id, restaurant_id=admin.restaurant_id).first()
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        # Update order status to cancelled
        order.status = 'cancelled'
        order.cancellation_reason = reason
        db.session.commit()
        
        # Log activity
        log_admin_activity(admin.id, 'payment_rejected', 'order', order_id, f'Payment rejected for order #{order_id}: {reason}')
        
        return jsonify({'success': True, 'message': 'Payment rejected successfully'})
    except Exception as e:
        logger.error(f"Error rejecting payment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/kitchen-staff', methods=['GET'])
@app.route('/api/admin/kitchen-staff-management', methods=['GET'])
@admin_required
def get_kitchen_staff_admin():
    """Get kitchen staff for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        logger.info(f"Getting kitchen staff for admin {admin.username} (ID: {admin.id}, Restaurant: {admin.restaurant_id})")
        
        # Get kitchen staff users for this restaurant
        kitchen_staff = AdminUser.query.filter_by(
            restaurant_id=admin.restaurant_id,
            role='kitchen_staff'
        ).all()
        
        logger.info(f"Found {len(kitchen_staff)} kitchen staff members")
        
        staff_data = []
        for staff in kitchen_staff:
            staff_data.append({
                'id': staff.id,
                'username': staff.username,
                'full_name': staff.full_name,
                'phone': staff.phone,
                'is_active': staff.is_active,
                'created_at': staff.created_at.isoformat() if staff.created_at else None
            })
        
        return jsonify({
            'success': True,
            'kitchen_staff': staff_data
        })
    except Exception as e:
        logger.error(f"Error getting kitchen staff: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/kitchen-staff', methods=['POST'])
@app.route('/api/admin/kitchen-staff-management', methods=['POST'])
@admin_required
def add_kitchen_staff_admin():
    """Add kitchen staff for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        data = request.get_json()
        
        # Check if username already exists
        if AdminUser.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        # Generate password hash
        password_hash = generate_password_hash(data['password'])
        
        # Create kitchen staff user
        kitchen_staff = AdminUser(
            username=data['username'],
            full_name=data['full_name'],
            phone=data.get('phone'),
            role='kitchen_staff',
            password_hash=password_hash,
            restaurant_id=admin.restaurant_id,
            is_active=True
        )
        
        db.session.add(kitchen_staff)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Kitchen staff added successfully',
            'staff': {
                'id': kitchen_staff.id,
                'username': kitchen_staff.username,
                'full_name': kitchen_staff.full_name,
                'phone': kitchen_staff.phone
            }
        })
    except Exception as e:
        logger.error(f"Error adding kitchen staff: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/kitchen-staff/<int:staff_id>', methods=['DELETE'])
@app.route('/api/admin/kitchen-staff-management/<int:staff_id>', methods=['DELETE'])
@admin_required
def delete_kitchen_staff_admin(staff_id):
    """Delete kitchen staff for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
        # Get kitchen staff user
        kitchen_staff = AdminUser.query.filter_by(
            id=staff_id,
            restaurant_id=admin.restaurant_id,
            role='kitchen_staff'
        ).first()
        
        if not kitchen_staff:
            return jsonify({'success': False, 'message': 'Kitchen staff not found'}), 404
        
        db.session.delete(kitchen_staff)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Kitchen staff deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting kitchen staff: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/kitchen-staff/<int:staff_id>', methods=['GET'])
@admin_required
def get_kitchen_staff_details(staff_id):
    """Get details of specific kitchen staff member"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        staff = AdminUser.query.filter_by(
            id=staff_id,
            restaurant_id=admin.restaurant_id,
            role='kitchen_staff'
        ).first()
        
        if not staff:
            return jsonify({'success': False, 'message': 'Kitchen staff not found'}), 404
        
        return jsonify({
            'success': True,
            'staff': {
                'id': staff.id,
                'username': staff.username,
                'full_name': staff.full_name,
                'phone': staff.phone,
                'is_active': staff.is_active,
                'created_at': staff.created_at.isoformat() if staff.created_at else None
            }
        })
    except Exception as e:
        logger.error(f"Error fetching kitchen staff details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/kitchen-staff/<int:staff_id>/update', methods=['PUT'])
@admin_required
def update_kitchen_staff_details(staff_id):
    """Update kitchen staff details"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        data = request.get_json()
        
        staff = AdminUser.query.filter_by(
            id=staff_id,
            restaurant_id=admin.restaurant_id,
            role='kitchen_staff'
        ).first()
        
        if not staff:
            return jsonify({'success': False, 'message': 'Kitchen staff not found'}), 404
        
        # Update staff details
        if 'full_name' in data:
            staff.full_name = data['full_name']
        if 'phone' in data:
            staff.phone = data['phone']
        if 'is_active' in data:
            staff.is_active = data['is_active']
        
        db.session.commit()
        
        log_admin_activity(
            admin.id,
            'kitchen_staff_updated',
            'kitchen_staff',
            staff_id,
            f'Updated kitchen staff: {staff.username}'
        )
        
        return jsonify({
            'success': True,
            'message': 'Kitchen staff updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating kitchen staff: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/kitchen-staff/<int:staff_id>/change-password', methods=['PUT'])
@admin_required
def change_kitchen_staff_password(staff_id):
    """Change password for kitchen staff member"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        data = request.get_json()
        
        staff = AdminUser.query.filter_by(
            id=staff_id,
            restaurant_id=admin.restaurant_id,
            role='kitchen_staff'
        ).first()
        
        if not staff:
            return jsonify({'success': False, 'message': 'Kitchen staff not found'}), 404
        
        new_password = data.get('new_password')
        notify_staff = data.get('notify_staff', False)
        
        if not new_password or len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400
        
        # Hash and update password
        from werkzeug.security import generate_password_hash
        staff.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        log_admin_activity(
            admin.id,
            'password_changed',
            'kitchen_staff',
            staff_id,
            f'Changed password for kitchen staff: {staff.username}'
        )
        
        # TODO: If notify_staff is True, send notification to staff member
        # This would require staff notification system implementation
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
    except Exception as e:
        logger.error(f"Error changing kitchen staff password: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/upload-kitchen-logo', methods=['POST'])
@admin_required
def upload_kitchen_logo():
    """Upload kitchen logo image"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
        if 'kitchen_logo' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['kitchen_logo']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Generate unique filename with timestamp
            import time
            timestamp = str(int(time.time()))
            filename = f"kitchen_logo_{timestamp}_{filename}"
            
            # Ensure uploads directory exists
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Update restaurant with kitchen logo
            restaurant = Restaurant.query.get(admin.restaurant_id)
            if restaurant:
                restaurant.kitchen_logo_url = f'/static/uploads/{filename}'
                db.session.commit()
            
            log_admin_activity(
                admin.id,
                'kitchen_logo_uploaded',
                'restaurant',
                admin.restaurant_id,
                f'Uploaded kitchen logo: {filename}'
            )
            
            return jsonify({
                'success': True,
                'message': 'Kitchen logo uploaded successfully',
                'image_url': f'/static/uploads/{filename}'
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid file type. Please upload an image.'}), 400
    except Exception as e:
        logger.error(f"Error uploading kitchen logo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/admin/analytics', methods=['GET'])
@admin_required
def get_admin_analytics():
    """Get analytics data for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
        from models import Order
        from datetime import datetime, timedelta
        
        # Get date range (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Orders analytics
        total_orders = Order.query.filter_by(restaurant_id=admin.restaurant_id).count()
        
        delivered_orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id,
            status='delivered'
        ).count()
        
        cancelled_orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id,
            status='cancelled'
        ).count()
        
        pending_orders = Order.query.filter_by(
            restaurant_id=admin.restaurant_id,
            status='pending'
        ).count()
        
        # Revenue analytics
        total_revenue = db.session.query(
            db.func.sum(Order.total_amount)
        ).filter_by(
            restaurant_id=admin.restaurant_id,
            status='delivered'
        ).scalar() or 0
        
        # Popular items
        popular_items = db.session.query(
            MenuItem.name,
            db.func.count(Order.id).label('order_count')
        ).join(
            Order, db.text("JSON_EXTRACT(orders.items, '$[*].name') LIKE '%' || menu_items.name || '%'")
        ).filter(
            MenuItem.restaurant_id == admin.restaurant_id,
            Order.status == 'delivered'
        ).group_by(MenuItem.name).order_by(
            db.text('order_count DESC')
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_orders': total_orders,
                'delivered_orders': delivered_orders,
                'cancelled_orders': cancelled_orders,
                'pending_orders': pending_orders,
                'total_revenue': float(total_revenue),
                'popular_items': [{'name': item.name, 'count': item.order_count} for item in popular_items]
            }
        })
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/settings', methods=['GET'])
@admin_required
def get_admin_settings():
    """Get settings for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        
        # Get restaurant settings
        restaurant = Restaurant.query.get(admin.restaurant_id)
        
        return jsonify({
            'success': True,
            'settings': {
                'restaurant_name': restaurant.name,
                'restaurant_address': restaurant.address,
                'restaurant_phone': restaurant.phone,
                'delivery_fee': restaurant.delivery_fee,
                'minimum_order': restaurant.minimum_order,
                'estimated_delivery_time': restaurant.estimated_delivery_time,
                'is_active': restaurant.is_active
            }
        })
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/settings', methods=['POST'])
@admin_required
def update_admin_settings():
    """Update settings for restaurant admin"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        data = request.get_json()
        
        # Update restaurant settings
        restaurant = Restaurant.query.get(admin.restaurant_id)
        
        if 'restaurant_name' in data:
            restaurant.name = data['restaurant_name']
        if 'restaurant_address' in data:
            restaurant.address = data['restaurant_address']
        if 'restaurant_phone' in data:
            restaurant.phone = data['restaurant_phone']
        if 'delivery_fee' in data:
            restaurant.delivery_fee = float(data['delivery_fee'])
        if 'minimum_order' in data:
            restaurant.minimum_order = float(data['minimum_order'])
        if 'estimated_delivery_time' in data:
            restaurant.estimated_delivery_time = data['estimated_delivery_time']
        if 'is_active' in data:
            restaurant.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/drivers/nearby', methods=['GET'])
@admin_required
def get_admin_nearby_drivers():
    """Get nearby drivers for restaurant admin based on restaurant location"""
    try:
        admin = AdminUser.query.get(session['admin_id'])
        restaurant = Restaurant.query.get(admin.restaurant_id)
        
        if not restaurant or not restaurant.latitude or not restaurant.longitude:
            return jsonify({'error': 'Restaurant location not set'}), 400
        
        # Get nearby drivers using the restaurant's location
        from datetime import datetime, timedelta
        recent_time = datetime.utcnow() - timedelta(minutes=10)
        
        drivers = Driver.query.filter(
            Driver.is_approved == True,
            Driver.is_active == True,
            Driver.current_lat.isnot(None),
            Driver.current_lng.isnot(None),
            Driver.last_location_update >= recent_time
        ).all()
        
        # Calculate distances from restaurant location
        nearby_drivers = []
        for driver in drivers:
            from routes import calculate_distance
            distance = calculate_distance(
                restaurant.latitude, restaurant.longitude,
                driver.current_lat, driver.current_lng
            )
            
            # Only include drivers within 10km radius
            if distance <= 10:
                # Determine driver status
                time_since_update = (datetime.utcnow() - driver.last_location_update).total_seconds()
                location_fresh = time_since_update < 300  # Less than 5 minutes
                
                if not driver.is_available:
                    status = 'Busy'
                    status_color = '#fd7e14'  # Orange
                elif not location_fresh:
                    status = 'Location Outdated'
                    status_color = '#dc3545'  # Red
                else:
                    status = 'Available'
                    status_color = '#198754'  # Green
                
                driver_data = {
                    'id': driver.id,
                    'name': driver.name,
                    'phone_number': driver.phone_number,
                    'vehicle_type': driver.vehicle_type,
                    'current_lat': driver.current_lat,
                    'current_lng': driver.current_lng,
                    'distance': round(distance, 2),
                    'last_location_update': driver.last_location_update.strftime('%H:%M:%S'),
                    'status': status,
                    'status_color': status_color,
                    'is_available': driver.is_available,
                    'telegram_user_id': driver.telegram_user_id,
                    'time_since_update': round(time_since_update / 60, 1)  # Minutes
                }
                nearby_drivers.append(driver_data)
        
        # Sort by distance (closest first)
        nearby_drivers.sort(key=lambda x: x['distance'])
        
        return jsonify({
            'success': True,
            'drivers': nearby_drivers,
            'total_nearby': len(nearby_drivers),
            'available_drivers': len([d for d in nearby_drivers if d['status'] == 'Available']),
            'restaurant_name': restaurant.name,
            'restaurant_location': {
                'latitude': restaurant.latitude,
                'longitude': restaurant.longitude
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching nearby drivers for admin: {e}")
        return jsonify({'error': 'Failed to fetch nearby drivers'}), 500