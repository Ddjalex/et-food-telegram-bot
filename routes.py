import os
import json
import csv
from io import StringIO
from datetime import datetime, timedelta
from flask import render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
from app import app
from extensions import db
from models import MenuItem, Order, AdminUser, UserProfile, Category, Driver
from bot_minimal import send_order_notification, notify_customer_status_change
from complete_order_workflow import process_new_order, handle_order_status_change
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
    """BeUdelivery-style driver notification system"""
    try:
        # Import the enhanced driver integration system
        from driver_integration_system import driver_system
        
        # Use the BeUdelivery-like notification system
        success = driver_system.notify_new_order(order_id)
        
        if success:
            logger.info(f"✅ Successfully notified drivers about order #{order_id}")
        else:
            logger.warning(f"⚠️ No drivers notified for order #{order_id}")
            
        return success
                
    except Exception as e:
        logger.error(f"Error in find_and_notify_nearby_drivers: {e}")
        return False

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

@app.route('/driver-registration')
def driver_registration():
    """Driver registration page"""
    return render_template('driver_registration.html')

@app.route('/enhanced-driver-panel')
def enhanced_driver_panel():
    """Enhanced driver panel with BeU delivery style"""
    return render_template('enhanced_driver_panel.html')

@app.route('/api/driver-registration', methods=['POST'])
def api_driver_registration():
    """API endpoint for driver registration"""
    try:
        telegram_id = request.form.get('telegram_id')
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        vehicle_type = request.form.get('vehicle_type')
        
        # Check if driver already exists
        existing_driver = Driver.query.filter_by(telegram_user_id=telegram_id).first()
        if existing_driver:
            return jsonify({'success': False, 'message': 'Driver already registered'})
        
        # Create new driver with required fields
        driver = Driver(
            name=name or "Driver Registration",
            phone_number=phone_number or "+251900000000", 
            telegram_user_id=int(telegram_id) if telegram_id else None,
            vehicle_type=vehicle_type or "motorcycle",
            is_active=True,
            is_available=False,  # Not available until approved
            is_approved=False,
            approval_status='pending'
        )
        
        # Handle file uploads
        upload_folder = os.path.join('static', 'driver_documents')
        os.makedirs(upload_folder, exist_ok=True)
        
        document_fields = ['licenseFront', 'licenseBack', 'idFront', 'idBack', 'vehicleReg']
        for field in document_fields:
            if field in request.files:
                file = request.files[field]
                if file and file.filename:
                    filename = secure_filename(f"{telegram_id}_{field}_{file.filename}")
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    
                    # Store document path in driver model
                    if field.startswith('license'):
                        driver.license_document = file_path
                    elif field.startswith('id'):
                        driver.id_document = file_path
                    elif field.startswith('vehicle'):
                        driver.vehicle_document = file_path
        
        db.session.add(driver)
        db.session.commit()
        
        # Send pending registration message
        from driver_registration import send_driver_registration_pending, notify_admin_driver_registration
        send_driver_registration_pending(telegram_id, name)
        
        # Notify admin
        notify_admin_driver_registration({
            'name': name,
            'phone_number': phone_number,
            'vehicle_type': vehicle_type,
            'documents_uploaded': True
        })
        
        return jsonify({'success': True, 'message': 'Registration submitted successfully'})
        
    except Exception as e:
        logger.error(f"Error in driver registration: {e}")
        return jsonify({'success': False, 'message': 'Registration failed'}), 500



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
        
        # Process new order through workflow manager
        process_new_order(order.id)
        
        return jsonify({'message': 'Order created successfully', 'order_id': order.id}), 201
    
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create order'}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status with automatic driver notification"""
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
        
        # Handle status change through workflow manager
        handle_order_status_change(order_id, old_status, new_status)
        
        # If order is confirmed, automatically find nearby drivers
        if new_status == 'confirmed' and old_status == 'pending':
            from complete_order_workflow import OrderWorkflowManager
            manager = OrderWorkflowManager()
            manager.find_nearby_drivers(order_id)
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} status updated from {old_status} to {new_status}',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status,
            'driver_notified': order.driver_id is not None if new_status in ['preparing', 'out_for_delivery'] else False
        })
    
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
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

# Driver Management API Endpoints
@app.route('/api/drivers/pending')
def get_pending_drivers():
    """Get pending drivers for admin approval"""
    try:
        pending_drivers = Driver.query.filter_by(approval_status='pending').all()
        return jsonify([{
            'id': driver.id,
            'name': driver.name,
            'phone_number': driver.phone_number,
            'telegram_user_id': driver.telegram_user_id,
            'vehicle_type': driver.vehicle_type,
            'created_at': driver.created_at.isoformat() if driver.created_at else None,
            'license_document': driver.license_document,
            'id_document': driver.id_document,
            'vehicle_document': driver.vehicle_document
        } for driver in pending_drivers])
    except Exception as e:
        logger.error(f"Error fetching pending drivers: {e}")
        return jsonify({'error': 'Failed to fetch pending drivers'}), 500

@app.route('/api/drivers/<int:driver_id>/approve', methods=['POST'])
def approve_driver_api(driver_id):
    """Approve a pending driver"""
    try:
        from admin_approval_system import approve_driver
        data = request.get_json()
        admin_id = data.get('admin_id', 383870190)  # Default admin ID
        
        success, message = approve_driver(driver_id, admin_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"Error approving driver: {e}")
        return jsonify({'success': False, 'message': 'Failed to approve driver'}), 500

@app.route('/api/drivers/<int:driver_id>/reject', methods=['POST'])
def reject_driver_api(driver_id):
    """Reject a pending driver"""
    try:
        from admin_approval_system import reject_driver
        data = request.get_json()
        admin_id = data.get('admin_id', 383870190)  # Default admin ID
        reason = data.get('reason', 'Application does not meet requirements')
        
        success, message = reject_driver(driver_id, admin_id, reason)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"Error rejecting driver: {e}")
        return jsonify({'success': False, 'message': 'Failed to reject driver'}), 500

@app.route('/api/drivers/<int:driver_id>/remove', methods=['DELETE'])
def remove_driver_api(driver_id):
    """Remove a driver employee"""
    try:
        driver = Driver.query.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': 'Driver not found'}), 404
            
        driver_name = driver.name
        driver_telegram_id = driver.telegram_user_id
        
        # Check if driver has active orders
        active_orders = Order.query.filter_by(driver_id=driver_id, status='assigned').count()
        if active_orders > 0:
            return jsonify({
                'success': False, 
                'message': f'Cannot remove driver with {active_orders} active orders. Please reassign orders first.'
            }), 400
        
        # Remove driver from database
        db.session.delete(driver)
        db.session.commit()
        
        # Send notification to driver if they have started the bot
        if driver_telegram_id:
            try:
                from driver_bot import send_driver_message
                message = f"📋 *Account Status Update*\n\n"
                message += f"Your driver account has been removed from ET-FOOD delivery system.\n\n"
                message += f"If you believe this is an error, please contact support.\n"
                message += f"Thank you for your service with ET-FOOD."
                
                send_driver_message(driver_telegram_id, message)
            except Exception as e:
                logger.warning(f"Could not notify removed driver {driver_telegram_id}: {e}")
        
        # Log the removal
        logger.info(f"Driver {driver_name} (ID: {driver_id}) removed by admin")
        
        return jsonify({
            'success': True, 
            'message': f'Driver {driver_name} has been removed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error removing driver: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to remove driver'}), 500

@app.route('/api/drivers')
def get_all_drivers():
    """Get all drivers for admin management"""
    try:
        drivers = Driver.query.all()
        return jsonify([{
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
        } for driver in drivers])
    except Exception as e:
        logger.error(f"Error fetching all drivers: {e}")
        return jsonify({'error': 'Failed to fetch drivers'}), 500

@app.route('/api/drivers/<int:driver_id>/unassign-orders', methods=['POST'])
def unassign_driver_orders(driver_id):
    """Unassign all active orders from a driver"""
    try:
        driver = Driver.query.get(driver_id)
        
        if not driver:
            return jsonify({'success': False, 'message': 'Driver not found'}), 404
            
        # Find all assigned orders for this driver
        assigned_orders = Order.query.filter_by(driver_id=driver_id, status='assigned').all()
        
        unassigned_count = 0
        for order in assigned_orders:
            order.driver_id = None
            order.status = 'confirmed'  # Reset to confirmed status
            unassigned_count += 1
            
            # Notify customer about order reassignment
            try:
                from bot_minimal import notify_customer_status_change
                notify_customer_status_change(order.id, 'confirmed')
            except Exception as e:
                logger.warning(f"Could not notify customer about order reassignment: {e}")
        
        # Make driver unavailable
        driver.is_available = False
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Successfully unassigned {unassigned_count} orders from {driver.name}',
            'unassigned_orders': unassigned_count
        })
        
    except Exception as e:
        logger.error(f"Error unassigning driver orders: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to unassign orders'}), 500

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

# Enhanced Driver Management APIs for BeU delivery style
@app.route('/api/drivers/telegram/<int:telegram_user_id>', methods=['GET'])
def get_driver_by_telegram_id(telegram_user_id):
    """Get driver by Telegram user ID"""
    try:
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        return jsonify({
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
            'created_at': driver.created_at.isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching driver: {e}")
        return jsonify({'error': 'Failed to fetch driver'}), 500

@app.route('/api/drivers/telegram/<int:telegram_user_id>/status', methods=['GET'])
def get_driver_status(telegram_user_id):
    """Get driver status"""
    try:
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        # Get active orders count
        active_orders = Order.query.filter_by(driver_id=driver.id).filter(
            Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
        ).count()
        
        # Check location freshness
        location_active = False
        if driver.last_location_update:
            time_diff = (datetime.utcnow() - driver.last_location_update).total_seconds()
            location_active = time_diff < 600  # Less than 10 minutes
        
        return jsonify({
            'driver_id': driver.id,
            'name': driver.name,
            'is_active': driver.is_active,
            'is_available': driver.is_available,
            'is_approved': driver.is_approved,
            'location_active': location_active,
            'active_orders_count': active_orders,
            'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None
        })
    except Exception as e:
        logger.error(f"Error fetching driver status: {e}")
        return jsonify({'error': 'Failed to fetch driver status'}), 500

@app.route('/api/drivers/telegram/<int:telegram_user_id>/toggle', methods=['POST'])
def toggle_driver_availability(telegram_user_id):
    """Toggle driver online/offline status"""
    try:
        data = request.get_json()
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        # Update availability
        driver.is_available = data.get('is_available', not driver.is_available)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_available': driver.is_available,
            'message': f"Driver is now {'ONLINE' if driver.is_available else 'OFFLINE'}"
        })
    except Exception as e:
        logger.error(f"Error toggling driver availability: {e}")
        return jsonify({'error': 'Failed to toggle availability'}), 500

@app.route('/api/drivers/telegram/<int:telegram_user_id>/location', methods=['POST'])
def update_driver_location(telegram_user_id):
    """Update driver location"""
    try:
        data = request.get_json()
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        # Update location
        driver.current_lat = data.get('lat')
        driver.current_lng = data.get('lng')
        driver.last_location_update = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Location updated successfully',
            'location': {
                'lat': driver.current_lat,
                'lng': driver.current_lng,
                'updated_at': driver.last_location_update.isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error updating driver location: {e}")
        return jsonify({'error': 'Failed to update location'}), 500

@app.route('/api/drivers/telegram/<int:telegram_user_id>/orders', methods=['GET'])
def get_driver_orders(telegram_user_id):
    """Get driver's orders"""
    try:
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        # Get active orders
        active_orders = Order.query.filter_by(driver_id=driver.id).filter(
            Order.status.in_(['pending', 'confirmed', 'preparing', 'out_for_delivery'])
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in active_orders:
            orders_data.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'customer_address': order.customer_address,
                'total_amount': order.total_amount,
                'payment_method': order.payment_method,
                'status': order.status,
                'location_lat': order.location_lat,
                'location_lng': order.location_lng,
                'items': order.items,
                'created_at': order.created_at.isoformat(),
                'estimated_delivery_time': order.estimated_delivery_time.isoformat() if order.estimated_delivery_time else None
            })
        
        return jsonify({
            'driver_id': driver.id,
            'orders': orders_data,
            'total_orders': len(orders_data)
        })
    except Exception as e:
        logger.error(f"Error fetching driver orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/orders/<int:order_id>/accept', methods=['POST'])
def accept_order(order_id):
    """Accept order by driver"""
    try:
        data = request.get_json()
        driver_telegram_id = data.get('driver_telegram_id')
        
        if not driver_telegram_id:
            return jsonify({'error': 'Driver Telegram ID required'}), 400
        
        # Find driver
        driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        # Get order
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Check if order is still pending
        if order.status != 'pending':
            return jsonify({'error': 'Order is no longer available'}), 400
        
        # Assign order to driver
        order.driver_id = driver.id
        order.status = 'confirmed'
        order.estimated_delivery_time = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()
        
        # Remove from pending orders in driver bot
        from driver_bot import pending_orders, order_timers
        pending_orders.pop(order_id, None)
        if order_id in order_timers:
            order_timers.pop(order_id, None)
        
        # Notify customer
        notify_customer_status_change(order_id, 'confirmed')
        
        # Send notification to driver bot
        from driver_bot import send_driver_message
        message = f"✅ *Order Accepted!*\n\n"
        message += f"📋 Order #{order_id}\n"
        message += f"👤 Customer: {order.customer_name}\n"
        message += f"📞 Phone: {order.customer_phone}\n"
        message += f"📍 Address: {order.customer_address}\n\n"
        message += f"🏪 **Next Steps:**\n"
        message += f"1️⃣ Go to ET-FOOD Kitchen for pickup\n"
        message += f"2️⃣ Call restaurant: +251-911-123-456\n"
        message += f"3️⃣ Confirm pickup when ready\n\n"
        message += f"💰 Delivery Amount: {order.total_amount:.2f} ETB"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Confirm Pickup",
                        "callback_data": f"pickup_complete_{order_id}"
                    }
                ],
                [
                    {
                        "text": "📞 Call Restaurant",
                        "callback_data": f"call_restaurant_{order_id}"
                    },
                    {
                        "text": "📞 Call Customer",
                        "callback_data": f"call_customer_{order_id}"
                    }
                ]
            ]
        }
        
        send_driver_message(driver_telegram_id, message, keyboard)
        
        return jsonify({
            'success': True,
            'message': 'Order accepted successfully',
            'order_id': order_id,
            'driver_id': driver.id
        })
    except Exception as e:
        logger.error(f"Error accepting order: {e}")
        return jsonify({'error': 'Failed to accept order'}), 500

@app.route('/api/orders/<int:order_id>/reject', methods=['POST'])
def reject_order(order_id):
    """Reject order by driver"""
    try:
        data = request.get_json()
        driver_telegram_id = data.get('driver_telegram_id')
        
        if not driver_telegram_id:
            return jsonify({'error': 'Driver Telegram ID required'}), 400
        
        # Remove from pending orders and reassign
        from driver_bot import pending_orders, order_timers, reassign_order_to_next_driver
        
        if order_id in pending_orders:
            pending_orders.pop(order_id, None)
        if order_id in order_timers:
            order_timers.pop(order_id, None)
        
        # Reassign to next driver
        reassign_order_to_next_driver(order_id)
        
        return jsonify({
            'success': True,
            'message': 'Order rejected and reassigned to another driver'
        })
    except Exception as e:
        logger.error(f"Error rejecting order: {e}")
        return jsonify({'error': 'Failed to reject order'}), 500

# Drivers Management
@app.route('/api/drivers', methods=['GET'])
def get_drivers():
    """Get all drivers with enhanced information for admin panel"""
    try:
        # Get all drivers (not just active ones) for comprehensive admin view
        drivers = Driver.query.all()
        return jsonify([{
            'id': driver.id,
            'name': driver.name,
            'phone_number': driver.phone_number,
            'telegram_user_id': driver.telegram_user_id,
            'vehicle_type': driver.vehicle_type,
            'is_active': driver.is_active,
            'is_available': driver.is_available,
            'is_approved': driver.is_approved,
            'approval_status': driver.approval_status,
            'license_document': driver.license_document,
            'id_document': driver.id_document,
            'vehicle_document': driver.vehicle_document,
            'rejection_reason': driver.rejection_reason,
            'current_lat': driver.current_lat,
            'current_lng': driver.current_lng,
            'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
            'created_at': driver.created_at.isoformat(),
            'updated_at': driver.updated_at.isoformat() if driver.updated_at else None,
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
        
        # Send welcome notification via driver bot if telegram_user_id is provided
        if driver.telegram_user_id:
            from driver_bot import send_driver_registration_notification
            send_driver_registration_notification(driver.telegram_user_id, driver.name, driver.phone_number)
        
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

# Driver Status and Availability Management Endpoints for Admin Dashboard
@app.route('/api/drivers/<int:driver_id>/status', methods=['PUT'])
def update_driver_status(driver_id):
    """Update driver active/inactive status"""
    try:
        data = request.get_json()
        is_active = data.get('is_active')
        
        if is_active is None:
            return jsonify({'error': 'is_active field is required'}), 400
        
        driver = Driver.query.get_or_404(driver_id)
        driver.is_active = is_active
        
        # If driver is set to inactive, also set as unavailable
        if not is_active:
            driver.is_available = False
        
        db.session.commit()
        
        # Notify driver via driver bot if telegram ID available
        if driver.telegram_user_id:
            try:
                from driver_bot import send_driver_message
                status_msg = f"📊 *Status Update*\n\nYour account is now {'ACTIVE' if is_active else 'INACTIVE'}"
                if not is_active:
                    status_msg += "\n\nYou will not receive order notifications while inactive."
                send_driver_message(driver.telegram_user_id, status_msg)
            except Exception as e:
                logger.error(f"Error notifying driver about status change: {e}")
        
        return jsonify({
            'success': True,
            'driver_id': driver_id,
            'is_active': is_active,
            'is_available': driver.is_available
        })
        
    except Exception as e:
        logger.error(f"Error updating driver status: {e}")
        return jsonify({'error': 'Failed to update driver status'}), 500

@app.route('/api/drivers/<int:driver_id>/availability', methods=['PUT'])
def update_driver_availability(driver_id):
    """Toggle driver availability (available/busy)"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        # Toggle availability
        driver.is_available = not driver.is_available
        
        # Driver must be active to be available
        if driver.is_available and not driver.is_active:
            driver.is_active = True
        
        db.session.commit()
        
        # Notify driver via driver bot if telegram ID available
        if driver.telegram_user_id:
            try:
                from driver_bot import send_driver_message
                status_msg = f"📊 *Availability Update*\n\nYou are now {'AVAILABLE' if driver.is_available else 'BUSY'}"
                if driver.is_available:
                    status_msg += "\n\nYou will receive new order notifications."
                else:
                    status_msg += "\n\nYou will not receive new order notifications until available."
                send_driver_message(driver.telegram_user_id, status_msg)
            except Exception as e:
                logger.error(f"Error notifying driver about availability change: {e}")
        
        return jsonify({
            'success': True,
            'driver_id': driver_id,
            'is_available': driver.is_available,
            'is_active': driver.is_active
        })
        
    except Exception as e:
        logger.error(f"Error updating driver availability: {e}")
        return jsonify({'error': 'Failed to update driver availability'}), 500

@app.route('/api/drivers/welcome-notification', methods=['POST'])
def send_welcome_notification():
    """Send welcome notification to new driver"""
    try:
        data = request.get_json()
        telegram_user_id = data.get('telegram_user_id')
        driver_name = data.get('driver_name')
        
        if not telegram_user_id or not driver_name:
            return jsonify({'error': 'telegram_user_id and driver_name are required'}), 400
        
        from driver_bot import send_driver_message
        
        welcome_message = f"""
🎉 *Welcome to ET-FOOD Driver System!*

Hello {driver_name}! You have been added as a delivery driver.

📋 *Your Registration:*
• Name: {driver_name}
• Status: Active
• Role: Delivery Driver

🚀 *Next Steps:*
1. Share your live location for order assignments
2. Accept delivery orders when they arrive
3. Use /help for commands and support

📱 *Important Commands:*
• /status - Check your current status
• /location - Share your location
• /help - Get help and support

Welcome to the team! 🏍️
"""
        
        send_driver_message(telegram_user_id, welcome_message)
        
        return jsonify({
            'success': True,
            'message': 'Welcome notification sent successfully'
        })
        
    except Exception as e:
        logger.error(f"Error sending welcome notification: {e}")
        return jsonify({'error': 'Failed to send welcome notification'}), 500

@app.route('/api/drivers/notify-status-change', methods=['POST'])
def notify_status_change():
    """Notify driver about status change via admin action"""
    try:
        data = request.get_json()
        driver_id = data.get('driver_id')
        status = data.get('status')
        
        driver = Driver.query.get_or_404(driver_id)
        
        if driver.telegram_user_id:
            from driver_bot import send_driver_message
            
            status_messages = {
                'activated': '✅ Your account has been activated by admin.',
                'deactivated': '❌ Your account has been deactivated by admin.',
                'available': '🟢 You are now available for deliveries.',
                'busy': '🔴 You are now marked as busy.'
            }
            
            message = f"📊 *Status Update*\n\n{status_messages.get(status, 'Your status has been updated.')}"
            send_driver_message(driver.telegram_user_id, message)
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error notifying driver about status change: {e}")
        return jsonify({'error': 'Failed to notify driver'}), 500

# Enhanced Driver Management API Endpoints

@app.route('/api/drivers/<int:driver_id>', methods=['GET'])
def get_driver_details(driver_id):
    """Get specific driver details for document viewing and management"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        return jsonify({
            'id': driver.id,
            'name': driver.name,
            'phone_number': driver.phone_number,
            'telegram_user_id': driver.telegram_user_id,
            'vehicle_type': driver.vehicle_type,
            'is_active': driver.is_active,
            'is_available': driver.is_available,
            'is_approved': driver.is_approved,
            'approval_status': driver.approval_status,
            'license_document': driver.license_document,
            'id_document': driver.id_document,
            'vehicle_document': driver.vehicle_document,
            'rejection_reason': driver.rejection_reason,
            'current_lat': driver.current_lat,
            'current_lng': driver.current_lng,
            'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
            'created_at': driver.created_at.isoformat(),
            'updated_at': driver.updated_at.isoformat() if driver.updated_at else None
        })
    except Exception as e:
        logger.error(f"Error fetching driver details: {e}")
        return jsonify({'error': 'Failed to fetch driver details'}), 500

@app.route('/api/drivers/<int:driver_id>/approve', methods=['POST'])
def approve_driver(driver_id):
    """Approve driver application and send notification"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        driver.is_approved = True
        driver.approval_status = 'approved'
        driver.approved_at = datetime.utcnow()
        driver.is_active = True  # Activate driver when approved
        driver.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send approval notification via driver bot
        if driver.telegram_user_id:
            try:
                from driver_bot import send_driver_message
                approval_message = f"""
🎉 *DRIVER APPLICATION APPROVED!*

Congratulations {driver.name}! Your application has been approved.

✅ *Account Status: ACTIVE*
🚚 *You can now receive delivery orders*

📍 *Next Steps:*
1. Share your live location to receive orders
2. Keep your availability status updated
3. Accept orders promptly when assigned

📱 *Quick Commands:*
• /status - Check your status
• /location - Share location
• /orders - View active orders
• /toggle - Change availability

Welcome to the ET-FOOD delivery team! 🏍️
"""
                send_driver_message(driver.telegram_user_id, approval_message)
            except Exception as e:
                logger.error(f"Failed to send approval notification: {e}")
        
        return jsonify({'success': True, 'message': 'Driver approved successfully'})
    except Exception as e:
        logger.error(f"Error approving driver: {e}")
        return jsonify({'error': 'Failed to approve driver'}), 500

@app.route('/api/drivers/<int:driver_id>/reject', methods=['POST'])
def reject_driver_application(driver_id):
    """Reject driver application with reason"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        data = request.get_json()
        
        driver.is_approved = False
        driver.approval_status = 'rejected'
        driver.rejection_reason = data.get('reason', 'Application rejected by admin')
        driver.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send rejection notification via driver bot
        if driver.telegram_user_id:
            try:
                from driver_bot import send_driver_message
                rejection_message = f"""
❌ *Application Status Update*

Your driver application has been rejected.

*Reason:* {driver.rejection_reason}

📞 *Next Steps:*
• Contact support for clarification
• Address the issues mentioned
• Reapply when requirements are met

Contact admin for more information.
"""
                send_driver_message(driver.telegram_user_id, rejection_message)
            except Exception as e:
                logger.error(f"Failed to send rejection notification: {e}")
        
        return jsonify({'success': True, 'message': 'Driver application rejected'})
    except Exception as e:
        logger.error(f"Error rejecting driver: {e}")
        return jsonify({'error': 'Failed to reject driver'}), 500

@app.route('/api/drivers/<int:driver_id>/orders', methods=['GET'])
def get_driver_active_orders(driver_id):
    """Get active orders assigned to specific driver"""
    try:
        orders = Order.query.filter_by(driver_id=driver_id).filter(
            Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
        ).order_by(Order.created_at.desc()).all()
        
        return jsonify([{
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'customer_address': order.customer_address,
            'total_amount': order.total_amount,
            'payment_method': order.payment_method,
            'status': order.status,
            'location_lat': order.location_lat,
            'location_lng': order.location_lng,
            'delivery_notes': order.delivery_notes,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'items': order.items
        } for order in orders])
    except Exception as e:
        logger.error(f"Error fetching driver orders: {e}")
        return jsonify({'error': 'Failed to fetch driver orders'}), 500

@app.route('/api/drivers/telegram/<int:telegram_user_id>/orders', methods=['GET'])
def get_driver_orders_by_telegram_id(telegram_user_id):
    """Get orders for driver by Telegram user ID (for driver panel)"""
    try:
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        orders = Order.query.filter_by(driver_id=driver.id).filter(
            Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
        ).order_by(Order.created_at.desc()).all()
        
        return jsonify([{
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'customer_address': order.customer_address,
            'total_amount': order.total_amount,
            'payment_method': order.payment_method,
            'status': order.status,
            'location_lat': order.location_lat,
            'location_lng': order.location_lng,
            'delivery_notes': order.delivery_notes,
            'created_at': order.created_at.isoformat(),
            'items': order.items
        } for order in orders])
    except Exception as e:
        logger.error(f"Error fetching driver orders by telegram ID: {e}")
        return jsonify({'error': 'Failed to fetch driver orders'}), 500

@app.route('/api/drivers/statistics', methods=['GET'])
def get_driver_statistics():
    """Get comprehensive driver statistics for admin dashboard"""
    try:
        total_drivers = Driver.query.count()
        active_drivers = Driver.query.filter_by(is_active=True).count()
        approved_drivers = Driver.query.filter_by(is_approved=True).count()
        pending_drivers = Driver.query.filter_by(is_approved=False, approval_status='pending').count()
        available_drivers = Driver.query.filter_by(is_active=True, is_available=True).count()
        busy_drivers = Driver.query.filter_by(is_active=True, is_available=False).count()
        
        # Online drivers (with recent location updates within 10 minutes)
        from datetime import datetime, timedelta
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        online_drivers = Driver.query.filter(
            Driver.is_active == True,
            Driver.last_location_update >= ten_minutes_ago
        ).count()
        
        offline_drivers = total_drivers - online_drivers
        
        return jsonify({
            'total': total_drivers,
            'active': active_drivers,
            'approved': approved_drivers,
            'pending': pending_drivers,
            'available': available_drivers,
            'busy': busy_drivers,
            'online': online_drivers,
            'offline': offline_drivers
        })
    except Exception as e:
        logger.error(f"Error fetching driver statistics: {e}")
        return jsonify({'error': 'Failed to fetch driver statistics'}), 500


