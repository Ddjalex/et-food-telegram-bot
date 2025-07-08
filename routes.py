import os
import json
import csv
from io import StringIO
from datetime import datetime
from flask import render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
from app import app
from extensions import db
from models import MenuItem, Order, AdminUser, UserProfile, Category, Driver
from bot_minimal import send_order_notification, notify_customer_status_change
import logging
import math
import threading
import time

logger = logging.getLogger(__name__)

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two coordinates in kilometers"""
    R = 6371  # Earth's radius in km
    dLat = math.radians(lat2 - lat1)
    dLng = math.radians(lng2 - lng1)
    a = (math.sin(dLat/2) * math.sin(dLat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dLng/2) * math.sin(dLng/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def find_and_notify_nearby_drivers(order_id):
    """Find available drivers and notify them about new order"""
    try:
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                return
            
            # Get all active and available drivers with recent location updates (last 10 minutes)
            from datetime import datetime, timedelta
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            
            available_drivers = Driver.query.filter_by(
                is_active=True,
                is_available=True,
                is_approved=True
            ).filter(
                Driver.telegram_user_id.isnot(None),
                Driver.last_location_update >= ten_minutes_ago,
                Driver.current_lat.isnot(None),
                Driver.current_lng.isnot(None)
            ).all()
            
            # Restaurant location (ET-FOOD Kitchen)
            restaurant_lat = 9.145
            restaurant_lng = 40.489658
            
            # Customer location
            customer_lat = order.location_lat or 9.165
            customer_lng = order.location_lng or 40.510
            
            # Calculate distance for each driver and sort by proximity
            drivers_with_distance = []
            for driver in available_drivers:
                # Use driver's current location (guaranteed to exist by query filter)
                driver_lat = driver.current_lat
                driver_lng = driver.current_lng
                
                # Calculate distance from driver to customer
                distance = calculate_distance(driver_lat, driver_lng, customer_lat, customer_lng)
                drivers_with_distance.append((driver, distance))
            
            # Sort by distance (nearest first)
            drivers_with_distance.sort(key=lambda x: x[1])
            
            # Take the nearest 3 drivers and notify them
            nearest_drivers = drivers_with_distance[:3]
            
            if nearest_drivers:
                # Prepare order data
                order_data = {
                    'id': order.id,
                    'customer_name': order.customer_name,
                    'customer_phone': order.customer_phone,
                    'customer_address': order.customer_address,
                    'total_amount': order.total_amount,
                    'payment_method': order.payment_method,
                    'location_lat': order.location_lat,
                    'location_lng': order.location_lng,
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else 'Just now',
                    'items': order.items
                }
                
                # Notify each nearby driver
                from driver_bot import notify_driver_assignment_via_driver_bot
                
                for driver, distance in nearest_drivers:
                    logger.info(f"Notifying driver {driver.name} (ID: {driver.telegram_user_id}) about order #{order.id}, distance: {distance:.1f}km")
                    
                    # Add distance to order data
                    order_data['distance'] = distance
                    
                    # Send notification using driver bot
                    notify_driver_assignment_via_driver_bot(driver.telegram_user_id, order_data)
                    
                    # Small delay between notifications to avoid spam
                    time.sleep(0.5)
                
                logger.info(f"Notified {len(nearest_drivers)} drivers about order #{order.id}")
            else:
                logger.warning(f"No available drivers with recent location updates found for order #{order.id}")
                
                # Send notification to admins about no drivers
                from bot_minimal import send_message_to_admin
                admin_message = f"⚠️ **No Available Drivers**\n\n"
                admin_message += f"Order #{order.id} could not be assigned to any drivers.\n\n"
                admin_message += f"**Reason:** No drivers with recent location updates (last 10 minutes)\n\n"
                admin_message += f"**Customer:** {order.customer_name}\n"
                admin_message += f"**Phone:** {order.customer_phone}\n"
                admin_message += f"**Total:** {order.total_amount} ETB\n\n"
                admin_message += f"**Action Required:** Ask drivers to share their location using the driver bot."
                
                # Send to all active admins
                try:
                    from models import AdminUser
                    admins = AdminUser.query.filter_by(is_active=True).all()
                    for admin in admins:
                        try:
                            send_message_to_admin(admin.telegram_user_id, admin_message)
                        except Exception as e:
                            logger.error(f"Error sending no-driver alert to admin {admin.telegram_user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error sending no-driver alerts to admins: {e}")
                
    except Exception as e:
        logger.error(f"Error in find_and_notify_nearby_drivers: {e}")

def notify_drivers_in_background(order_id):
    """Run driver notification in background thread"""
    thread = threading.Thread(target=find_and_notify_nearby_drivers, args=(order_id,))
    thread.daemon = True
    thread.start()

@app.route('/')
def index():
    """Main page"""
    return render_template('webapp_modern_fixed.html')

@app.route('/test')
def test():
    """Test page"""
    return render_template('test.html')

@app.route('/webapp')
def webapp():
    """Telegram WebApp page"""
    return render_template('webapp_modern_fixed.html')

@app.route('/admin')
def admin():
    """Admin dashboard"""
    return render_template('admin_fixed.html')

@app.route('/api/menu')
def get_menu():
    """Get menu items"""
    try:
        menu_items = MenuItem.query.filter_by(available=True).all()
        return jsonify([item.to_dict() for item in menu_items])
    except Exception as e:
        logger.error(f"Error fetching menu: {e}")
        return jsonify({'error': 'Failed to fetch menu'}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders for admin"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        query = Order.query
        if status:
            query = query.filter_by(status=status)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': orders.page
        })
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create new order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['telegram_user_id', 'customer_name', 'customer_phone', 'customer_address', 'items', 'payment_method']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Calculate total amount
        total_amount = 0
        for item in data['items']:
            total_amount += item['price'] * item['quantity']
        
        # Create order
        order = Order(
            telegram_user_id=data['telegram_user_id'],
            customer_name=data['customer_name'],
            customer_phone=data['customer_phone'],
            customer_address=data['customer_address'],
            items=data['items'],
            total_amount=total_amount,
            payment_method=data['payment_method'],
            transaction_id=data.get('transaction_id'),
            transaction_image_url=data.get('transaction_image_url'),
            location_lat=data.get('location_lat'),
            location_lng=data.get('location_lng')
        )
        
        db.session.add(order)
        db.session.commit()
        
        # Send notification to admins
        send_order_notification(order.id)
        
        # Automatically find and notify nearby drivers in background
        notify_drivers_in_background(order.id)
        
        return jsonify({'message': 'Order created successfully', 'order_id': order.id}), 201
    
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create order'}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        valid_statuses = ['pending', 'confirmed', 'preparing', 'out_for_delivery', 'delivered', 'cancelled']
        
        if not new_status or new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        order = Order.query.get_or_404(order_id)
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Notify customer about status change (if bot is configured)
        try:
            notify_customer_status_change(order_id, new_status)
        except Exception as bot_error:
            print(f"Bot notification failed: {bot_error}")
        
        return jsonify({
            'message': f'Order #{order_id} status updated from {old_status} to {new_status}',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status
        })
    
    except Exception as e:
        print(f"Error updating order status: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update order status'}), 500

@app.route('/api/orders/<int:order_id>')
def get_order(order_id):
    """Get specific order"""
    try:
        order = Order.query.get_or_404(order_id)
        return jsonify(order.to_dict())
    except Exception as e:
        logger.error(f"Error fetching order: {e}")
        return jsonify({'error': 'Failed to fetch order'}), 500

@app.route('/api/orders/user/<int:user_id>')
def get_user_orders(user_id):
    """Get orders for specific user"""
    try:
        orders = Order.query.filter_by(telegram_user_id=user_id).order_by(Order.created_at.desc()).all()
        return jsonify([order.to_dict() for order in orders])
    except Exception as e:
        logger.error(f"Error fetching user orders: {e}")
        return jsonify({'error': 'Failed to fetch user orders'}), 500

@app.route('/api/user-orders/<int:user_id>')
def get_user_orders_alt(user_id):
    """Get orders for specific user (alternative endpoint)"""
    try:
        orders = Order.query.filter_by(telegram_user_id=user_id).order_by(Order.created_at.desc()).all()
        return jsonify([order.to_dict() for order in orders])
    except Exception as e:
        logger.error(f"Error fetching user orders: {e}")
        return jsonify({'error': 'Failed to fetch user orders'}), 500

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """Upload image file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to avoid naming conflicts
            timestamp = str(int(datetime.now().timestamp()))
            filename = f"{timestamp}_{filename}"
            
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Return the URL path for the uploaded image
            image_url = f"/static/uploads/{filename}"
            return jsonify({'image_url': image_url}), 200
        else:
            return jsonify({'error': 'Invalid file type. Only PNG, JPG, JPEG, GIF, and WebP files are allowed'}), 400
            
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({'error': 'Failed to upload image'}), 500

@app.route('/api/menu', methods=['POST'])
def add_menu_item():
    """Add new menu item"""
    try:
        data = request.get_json()
        
        item = MenuItem(
            name=data['name'],
            price=float(data['price']),
            description=data.get('description', ''),
            image_url=data.get('image_url', ''),
            category=data.get('category', 'burgers'),
            available=data.get('available', True)
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({'message': 'Menu item added successfully', 'item_id': item.id}), 201
    
    except Exception as e:
        logger.error(f"Error adding menu item: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add menu item'}), 500

@app.route('/api/menu/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    """Update menu item"""
    try:
        data = request.get_json()
        item = MenuItem.query.get_or_404(item_id)
        
        item.name = data.get('name', item.name)
        item.price = float(data.get('price', item.price))
        item.description = data.get('description', item.description)
        item.image_url = data.get('image_url', item.image_url)
        item.category = data.get('category', item.category)
        item.available = data.get('available', item.available)
        
        db.session.commit()
        
        return jsonify({'message': 'Menu item updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating menu item: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update menu item'}), 500

@app.route('/api/menu/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    """Delete menu item"""
    try:
        item = MenuItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({'message': 'Menu item deleted successfully'})
    
    except Exception as e:
        logger.error(f"Error deleting menu item: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete menu item'}), 500

@app.route('/api/telegram-user-photo/<int:user_id>')
def get_telegram_user_photo(user_id):
    """Get Telegram user profile photo"""
    try:
        # This is a placeholder endpoint for Telegram photo access
        # In a real implementation, you would use Telegram Bot API
        # For now, return a generic response
        return jsonify({
            'error': 'Photo access requires Telegram Bot token configuration',
            'photo_url': None
        }), 404
    
    except Exception as e:
        logger.error(f"Error fetching user photo: {e}")
        return jsonify({'error': 'Failed to fetch user photo'}), 500

@app.route('/api/orders/export')
def export_orders():
    """Export orders to CSV"""
    try:
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Order ID', 'Customer Name', 'Phone', 'Address', 'Total Amount', 'Status', 'Payment Method', 'Created At'])
        
        # Write data
        orders = Order.query.all()
        for order in orders:
            writer.writerow([
                order.id,
                order.customer_name,
                order.customer_phone,
                order.customer_address,
                order.total_amount,
                order.status,
                order.payment_method,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        output.seek(0)
        return send_file(
            StringIO(output.getvalue()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='orders.csv'
        )
    
    except Exception as e:
        logger.error(f"Error exporting orders: {e}")
        return jsonify({'error': 'Failed to export orders'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# Categories Management
@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    try:
        categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order).all()
        return jsonify([{
            'id': cat.id,
            'name': cat.name,
            'description': cat.description,
            'icon': cat.icon,
            'image_url': cat.image_url,
            'sort_order': cat.sort_order
        } for cat in categories])
    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        return jsonify({'error': 'Failed to fetch categories'}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Create new category"""
    try:
        data = request.get_json()
        category = Category(
            name=data['name'],
            description=data.get('description', ''),
            icon=data.get('icon', '🍽️'),
            image_url=data.get('image_url'),
            sort_order=data.get('sort_order', 0)
        )
        db.session.add(category)
        db.session.commit()
        
        return jsonify({'success': True, 'category_id': category.id})
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return jsonify({'error': 'Failed to create category'}), 500

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """Update category"""
    try:
        data = request.get_json()
        category = Category.query.get(category_id)
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Update category fields
        category.name = data.get('name', category.name)
        category.description = data.get('description', category.description)
        category.icon = data.get('icon', category.icon)
        category.image_url = data.get('image_url', category.image_url)
        category.sort_order = data.get('sort_order', category.sort_order)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Category updated successfully'})
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        return jsonify({'error': 'Failed to update category'}), 500

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Delete category"""
    try:
        category = Category.query.get(category_id)
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Check if category has associated menu items
        menu_items = MenuItem.query.filter_by(category=category.name.lower()).first()
        if menu_items:
            return jsonify({'error': 'Cannot delete category that has menu items'}), 400
        
        # Soft delete - set is_active to False
        category.is_active = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Category deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        return jsonify({'error': 'Failed to delete category'}), 500

# Drivers Management
@app.route('/api/drivers', methods=['GET'])
def get_drivers():
    """Get all drivers"""
    try:
        drivers = Driver.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': driver.id,
            'name': driver.name,
            'phone_number': driver.phone_number,
            'vehicle_type': driver.vehicle_type,
            'is_available': driver.is_available,
            'is_approved': driver.is_approved,
            'approval_status': driver.approval_status,
            'license_document': driver.license_document,
            'id_document': driver.id_document,
            'vehicle_document': driver.vehicle_document,
            'rejection_reason': driver.rejection_reason,
            'current_location': {
                'lat': driver.current_lat,
                'lng': driver.current_lng,
                'last_update': driver.last_location_update.isoformat() if driver.last_location_update else None
            } if driver.current_lat and driver.current_lng else None
        } for driver in drivers])
    except Exception as e:
        logger.error(f"Error fetching drivers: {e}")
        return jsonify({'error': 'Failed to fetch drivers'}), 500

@app.route('/api/drivers', methods=['POST'])
def create_driver():
    """Create new driver"""
    try:
        data = request.get_json()
        driver = Driver(
            name=data['name'],
            phone_number=data['phone_number'],
            vehicle_type=data.get('vehicle_type', 'motorcycle'),
            telegram_user_id=data.get('telegram_user_id'),
            license_document=data.get('license_document'),
            id_document=data.get('id_document'),
            vehicle_document=data.get('vehicle_document')
        )
        db.session.add(driver)
        db.session.commit()
        
        return jsonify({'success': True, 'driver_id': driver.id})
    except Exception as e:
        logger.error(f"Error creating driver: {e}")
        return jsonify({'error': 'Failed to create driver'}), 500

@app.route('/api/drivers/<int:driver_id>/assign/<int:order_id>', methods=['POST'])
def assign_driver_to_order(driver_id, order_id):
    """Assign driver to order"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        order = Order.query.get_or_404(order_id)
        
        if not driver.is_available:
            return jsonify({'error': 'Driver is not available'}), 400
        
        order.driver_id = driver_id
        order.status = 'out_for_delivery'
        driver.is_available = False
        
        db.session.commit()
        
        # Notify customer about driver assignment
        notify_customer_status_change(order_id, 'out_for_delivery')
        
        # Notify driver about assignment using driver bot
        if driver.telegram_user_id:
            from driver_bot import notify_driver_assignment_via_driver_bot
            order_data = {
                'id': order.id,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'customer_address': order.customer_address,
                'total_amount': order.total_amount,
                'location_lat': order.location_lat,
                'location_lng': order.location_lng,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S') if order.created_at else 'Just now'
            }
            notify_driver_assignment_via_driver_bot(driver.telegram_user_id, order_data)
        
        return jsonify({'success': True, 'message': f'Driver {driver.name} assigned to order #{order_id}'})
    except Exception as e:
        logger.error(f"Error assigning driver: {e}")
        return jsonify({'error': 'Failed to assign driver'}), 500

@app.route('/api/drivers/<int:driver_id>/request-location', methods=['POST'])
def request_driver_location_api(driver_id):
    """Request location from driver via API"""
    try:
        from bot_minimal import request_driver_location
        request_driver_location(driver_id)
        return jsonify({'success': True, 'message': 'Location request sent to driver'})
    except Exception as e:
        logger.error(f"Error requesting driver location: {e}")
        return jsonify({'error': 'Failed to request location'}), 500

# Driver Panel Routes
@app.route('/driver-panel')
def driver_panel():
    """Driver panel WebApp page"""
    return render_template('driver_panel.html')

@app.route('/api/drivers/<int:driver_id>/orders')
def get_driver_orders(driver_id):
    """Get orders assigned to specific driver"""
    try:
        orders = Order.query.filter_by(driver_id=driver_id).filter(
            Order.status.in_(['pending', 'accepted', 'confirmed', 'preparing', 'out_for_delivery'])
        ).all()
        
        return jsonify({
            'orders': [order.to_dict() for order in orders]
        })
    except Exception as e:
        logger.error(f"Error fetching driver orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/drivers/telegram/<int:telegram_user_id>/orders')
def get_driver_orders_by_telegram(telegram_user_id):
    """Get orders assigned to driver by telegram user ID"""
    try:
        # Find driver by telegram user ID
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        if not driver:
            return jsonify({'orders': []})
        
        orders = Order.query.filter_by(driver_id=driver.id).filter(
            Order.status.in_(['pending', 'accepted', 'confirmed', 'preparing', 'out_for_delivery'])
        ).all()
        
        return jsonify({
            'orders': [order.to_dict() for order in orders]
        })
    except Exception as e:
        logger.error(f"Error fetching driver orders by telegram ID: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/driver/accept-order', methods=['POST'])
def driver_accept_order():
    """Handle order acceptance by driver"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        driver_telegram_id = data.get('driver_id')
        
        # Find driver by telegram ID
        driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
            
        # Check if driver is available
        if not driver.is_available:
            return jsonify({'error': 'Driver is not available'}), 400
            
        # Update order
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Check if order is still pending (not already accepted by another driver)
        if order.status != 'pending':
            return jsonify({'error': 'Order already accepted by another driver'}), 400
            
        if order.driver_id is not None:
            return jsonify({'error': 'Order already assigned to another driver'}), 400
        
        # Assign order to driver
        order.driver_id = driver.id
        order.status = 'out_for_delivery'
        driver.is_available = False
        
        db.session.commit()
        
        # Notify customer about driver assignment
        from bot_minimal import notify_customer_status_change
        notify_customer_status_change(order_id, 'out_for_delivery')
        
        # Send confirmation to driver
        from driver_bot import send_driver_message
        confirmation_msg = f"✅ *Order Accepted!*\n\n"
        confirmation_msg += f"You have successfully accepted Order #{order.id}\n"
        confirmation_msg += f"Customer: {order.customer_name}\n"
        confirmation_msg += f"Phone: {order.customer_phone}\n"
        confirmation_msg += f"Address: {order.customer_address}\n\n"
        confirmation_msg += f"Please proceed to ET-FOOD Kitchen to pick up the order."
        
        send_driver_message(driver_telegram_id, confirmation_msg)
        
        logger.info(f"Order #{order.id} accepted by driver {driver.name} (ID: {driver.telegram_user_id})")
        
        return jsonify({'success': True, 'message': 'Order accepted successfully'})
        
    except Exception as e:
        logger.error(f"Error accepting order: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to accept order'}), 500

@app.route('/api/driver/reject-order', methods=['POST'])
def driver_reject_order():
    """Handle order rejection by driver"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        # TODO: Implement order reassignment logic
        
        return jsonify({'success': True, 'message': 'Order rejected'})
        
    except Exception as e:
        logger.error(f"Error rejecting order: {e}")
        return jsonify({'error': 'Failed to reject order'}), 500

@app.route('/api/override-bot-delivery', methods=['POST'])
def override_bot_delivery():
    """Override automated bot delivery and assign to human driver"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Find the delivery bot driver
        bot_driver = Driver.query.filter_by(name='Delivery Bot').first()
        if order.driver_id == bot_driver.id:
            # Reset order to pending and make bot available
            order.driver_id = None
            order.status = 'pending'
            bot_driver.is_available = True
            
            db.session.commit()
            
            # Notify admins about override
            from bot_minimal import send_order_notification
            send_order_notification(order_id)
            
            return jsonify({'success': True, 'message': 'Bot delivery overridden successfully'})
        else:
            return jsonify({'error': 'Order is not assigned to delivery bot'}), 400
            
    except Exception as e:
        logger.error(f"Error overriding bot delivery: {e}")
        return jsonify({'error': 'Failed to override bot delivery'})

# Admin Driver Management and Live Status Control
@app.route('/api/admin/drivers/status', methods=['GET'])
def get_drivers_status():
    """Get live status of all drivers for admin"""
    try:
        drivers = Driver.query.all()
        
        drivers_data = []
        for driver in drivers:
            driver_data = {
                'id': driver.id,
                'name': driver.name,
                'phone_number': driver.phone_number,
                'telegram_user_id': driver.telegram_user_id,
                'vehicle_type': driver.vehicle_type,
                'is_active': driver.is_active,
                'is_available': driver.is_available,
                'is_approved': driver.is_approved,
                'approval_status': driver.approval_status,
                'current_lat': driver.current_lat,
                'current_lng': driver.current_lng,
                'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
                'created_at': driver.created_at.isoformat() if driver.created_at else None
            }
            
            # Get current active orders for this driver
            active_orders = Order.query.filter_by(driver_id=driver.id).filter(
                Order.status.in_(['out_for_delivery', 'preparing', 'confirmed'])
            ).all()
            
            driver_data['active_orders'] = len(active_orders)
            driver_data['current_orders'] = [
                {
                    'id': order.id,
                    'customer_name': order.customer_name,
                    'status': order.status,
                    'total_amount': order.total_amount,
                    'created_at': order.created_at.isoformat() if order.created_at else None
                }
                for order in active_orders
            ]
            
            drivers_data.append(driver_data)
        
        return jsonify({
            'drivers': drivers_data,
            'total_drivers': len(drivers_data),
            'active_drivers': len([d for d in drivers_data if d['is_active']]),
            'available_drivers': len([d for d in drivers_data if d['is_available']])
        })
        
    except Exception as e:
        logger.error(f"Error getting drivers status: {e}")
        return jsonify({'error': 'Failed to get drivers status'}), 500

@app.route('/api/admin/drivers/<int:driver_id>/toggle-status', methods=['POST'])
def toggle_driver_status(driver_id):
    """Toggle driver active/inactive status"""
    try:
        data = request.get_json()
        status_type = data.get('status_type')  # 'active' or 'available'
        new_status = data.get('status')
        
        driver = Driver.query.get_or_404(driver_id)
        
        if status_type == 'active':
            driver.is_active = new_status
            if not new_status:
                driver.is_available = False  # If inactive, also unavailable
        elif status_type == 'available':
            driver.is_available = new_status
        else:
            return jsonify({'error': 'Invalid status type'}), 400
        
        db.session.commit()
        
        # Notify driver about status change
        if driver.telegram_user_id:
            from driver_bot import send_driver_message
            status_msg = f"📊 *Status Update*\n\n"
            if status_type == 'active':
                status_msg += f"Your account is now {'ACTIVE' if new_status else 'INACTIVE'}\n"
            else:
                status_msg += f"Your availability is now {'AVAILABLE' if new_status else 'UNAVAILABLE'}\n"
            
            send_driver_message(driver.telegram_user_id, status_msg)
        
        return jsonify({
            'success': True, 
            'message': f'Driver {status_type} status updated successfully',
            'driver_id': driver_id,
            'new_status': new_status
        })
        
    except Exception as e:
        logger.error(f"Error toggling driver status: {e}")
        return jsonify({'error': 'Failed to update driver status'}), 500

@app.route('/api/admin/drivers/<int:driver_id>/location', methods=['GET'])
def get_driver_location(driver_id):
    """Get specific driver's current location"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        return jsonify({
            'driver_id': driver_id,
            'name': driver.name,
            'current_lat': driver.current_lat,
            'current_lng': driver.current_lng,
            'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
            'is_active': driver.is_active,
            'is_available': driver.is_available
        })
        
    except Exception as e:
        logger.error(f"Error getting driver location: {e}")
        return jsonify({'error': 'Failed to get driver location'}), 500

@app.route('/api/admin/drivers/live-tracking', methods=['GET'])
def get_live_tracking_data():
    """Get real-time tracking data for all drivers"""
    try:
        drivers = Driver.query.filter_by(is_active=True).all()
        
        tracking_data = []
        for driver in drivers:
            if driver.current_lat and driver.current_lng:
                # Get current order for this driver
                current_order = Order.query.filter_by(driver_id=driver.id).filter(
                    Order.status == 'out_for_delivery'
                ).first()
                
                driver_tracking = {
                    'driver_id': driver.id,
                    'name': driver.name,
                    'phone_number': driver.phone_number,
                    'vehicle_type': driver.vehicle_type,
                    'current_lat': driver.current_lat,
                    'current_lng': driver.current_lng,
                    'last_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
                    'is_available': driver.is_available,
                    'current_order': None
                }
                
                if current_order:
                    driver_tracking['current_order'] = {
                        'id': current_order.id,
                        'customer_name': current_order.customer_name,
                        'customer_address': current_order.customer_address,
                        'customer_lat': current_order.location_lat,
                        'customer_lng': current_order.location_lng,
                        'total_amount': current_order.total_amount,
                        'estimated_delivery_time': current_order.estimated_delivery_time.isoformat() if current_order.estimated_delivery_time else None
                    }
                
                tracking_data.append(driver_tracking)
        
        return jsonify({
            'drivers': tracking_data,
            'timestamp': datetime.utcnow().isoformat(),
            'total_tracking': len(tracking_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting live tracking data: {e}")
        return jsonify({'error': 'Failed to get live tracking data'}), 500

@app.route('/api/admin/drivers/add', methods=['POST'])
def add_driver_employee():
    """Add new driver employee from admin panel"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'phone_number', 'telegram_user_id', 'vehicle_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate telegram_user_id is a valid integer
        try:
            telegram_user_id = int(data['telegram_user_id'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid Telegram User ID'}), 400
        
        # Check if driver with this telegram_user_id already exists
        existing_driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        if existing_driver:
            return jsonify({'error': 'Driver with this Telegram ID already exists'}), 409
        
        # Create new driver
        new_driver = Driver(
            name=data['name'].strip(),
            phone_number=data['phone_number'].strip(),
            telegram_user_id=telegram_user_id,
            vehicle_type=data['vehicle_type'],
            is_active=True,
            is_available=True,
            is_approved=data.get('auto_approve', True),
            approval_status='approved' if data.get('auto_approve', True) else 'pending'
        )
        
        db.session.add(new_driver)
        db.session.commit()
        
        # Send welcome message to driver via driver bot
        try:
            from driver_bot import send_driver_message
            
            welcome_message = f"""
🎉 *Welcome to ET-FOOD Driver System!*

Hello {new_driver.name}! You have been added as a delivery driver for ET-FOOD.

📋 *Your Details:*
• Name: {new_driver.name}
• Phone: {new_driver.phone_number}
• Vehicle: {new_driver.vehicle_type.title()}
• Status: {'Approved' if new_driver.is_approved else 'Pending Approval'}

🚀 *How to Use:*
• You will receive notifications about new delivery orders
• Accept orders by clicking the "Accept" button
• Use the driver panel to manage your orders
• Share your location when requested

📱 *Commands:*
• /start - Show main menu
• /help - Get help and support
• /status - Check your current status

Welcome to the team! 🏍️
"""
            
            send_driver_message(telegram_user_id, welcome_message)
            logger.info(f"Welcome message sent to new driver {new_driver.name} (ID: {telegram_user_id})")
            
        except Exception as e:
            logger.error(f"Error sending welcome message to driver: {e}")
            # Continue without failing the entire operation
        
        return jsonify({
            'success': True,
            'message': 'Driver added successfully',
            'driver_id': new_driver.id,
            'driver_name': new_driver.name
        })
        
    except Exception as e:
        logger.error(f"Error adding driver employee: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add driver employee'}), 500

@app.route('/api/admin/orders/clear-previous', methods=['POST'])
def clear_previous_orders():
    """Clear previous orders (delivered, cancelled) from admin dashboard"""
    try:
        data = request.get_json()
        
        # Get filter criteria
        clear_delivered = data.get('clear_delivered', True)
        clear_cancelled = data.get('clear_cancelled', True)
        time_filter = data.get('time_filter', '7_days')  # Default: 7 days
        clear_all = data.get('clear_all', False)  # Clear all regardless of time
        
        # Calculate date threshold
        from datetime import datetime, timedelta
        
        if clear_all:
            # No time filter, clear all matching orders
            date_threshold = None
        else:
            # Time-based filtering
            if time_filter == '1_hour':
                date_threshold = datetime.utcnow() - timedelta(hours=1)
            elif time_filter == '24_hours':
                date_threshold = datetime.utcnow() - timedelta(hours=24)
            elif time_filter == '7_days':
                date_threshold = datetime.utcnow() - timedelta(days=7)
            else:
                return jsonify({'error': 'Invalid time filter'}), 400
        
        # Build query for orders to clear
        query = Order.query
        
        # Apply time filter if not clearing all
        if date_threshold is not None:
            query = query.filter(Order.created_at < date_threshold)
        
        # Add status filters
        status_filters = []
        if clear_delivered:
            status_filters.append('delivered')
        if clear_cancelled:
            status_filters.append('cancelled')
        
        if status_filters:
            query = query.filter(Order.status.in_(status_filters))
        else:
            return jsonify({'error': 'No order types selected for clearing'}), 400
        
        # Get orders to be cleared
        orders_to_clear = query.all()
        orders_count = len(orders_to_clear)
        
        if orders_count == 0:
            time_desc = 'any time' if clear_all else f'older than {time_filter.replace("_", " ")}'
            return jsonify({
                'success': True,
                'message': f'No orders found matching the criteria ({time_desc})',
                'cleared_count': 0
            })
        
        # Store order details for logging
        cleared_orders = []
        for order in orders_to_clear:
            cleared_orders.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'total_amount': order.total_amount,
                'status': order.status,
                'created_at': order.created_at.isoformat()
            })
        
        # Delete orders
        for order in orders_to_clear:
            db.session.delete(order)
        
        db.session.commit()
        
        # Log the clearing operation
        time_desc = 'from all time' if clear_all else f'older than {time_filter.replace("_", " ")}'
        logger.info(f"Cleared {orders_count} orders {time_desc}: {[o['id'] for o in cleared_orders]}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully cleared {orders_count} orders {time_desc}',
            'cleared_count': orders_count,
            'cleared_orders': cleared_orders
        })
        
    except Exception as e:
        logger.error(f"Error clearing previous orders: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to clear previous orders'}), 500

@app.route('/api/admin/orders/<int:order_id>/delete', methods=['DELETE'])
def delete_single_order(order_id):
    """Delete a single order by ID"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Store order info for logging
        order_info = {
            'id': order.id,
            'customer_name': order.customer_name,
            'status': order.status,
            'total_amount': order.total_amount,
            'created_at': order.created_at.isoformat()
        }
        
        # Delete the order
        db.session.delete(order)
        db.session.commit()
        
        logger.info(f"Deleted order #{order_id}: {order_info}")
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} deleted successfully',
            'deleted_order': order_info
        })
        
    except Exception as e:
        logger.error(f"Error deleting order #{order_id}: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to delete order #{order_id}'}), 500

