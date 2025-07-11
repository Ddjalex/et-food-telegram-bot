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

@app.route('/driver-registration/<int:chat_id>')
def driver_registration(chat_id):
    """Driver registration form"""
    return render_template('driver_registration.html', chat_id=chat_id)

@app.route('/api/driver-registration', methods=['POST'])
def submit_driver_registration():
    """Handle driver registration form submission"""
    try:
        # Get form data
        chat_id = request.form.get('chat_id')
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        vehicle_type = request.form.get('vehicle_type')
        license_front = request.files.get('license_front')
        license_back = request.files.get('license_back')
        id_front = request.files.get('id_front')
        id_back = request.files.get('id_back')
        vehicle_registration = request.files.get('vehicle_registration')
        
        # Handle file uploads
        document_urls = {}
        files = {
            'license_front': license_front,
            'license_back': license_back,
            'id_front': id_front,
            'id_back': id_back,
            'vehicle_registration': vehicle_registration
        }
        
        for doc_type, file in files.items():
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = str(int(datetime.now().timestamp()))
                filename = f"{timestamp}_{doc_type}_{filename}"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                document_urls[doc_type] = f"/static/uploads/{filename}"
        
        # Create driver record
        driver = Driver(
            name=name,
            phone_number=phone,
            email=email,
            vehicle_type=vehicle_type,
            telegram_user_id=int(chat_id),
            approval_status='pending',
            is_approved=False,
            is_active=False,
            is_available=False,
            license_front_url=document_urls.get('license_front', ''),
            license_back_url=document_urls.get('license_back', ''),
            id_front_url=document_urls.get('id_front', ''),
            id_back_url=document_urls.get('id_back', ''),
            vehicle_registration_url=document_urls.get('vehicle_registration', ''),
            created_at=datetime.utcnow()
        )
        
        db.session.add(driver)
        db.session.commit()
        
        # Notify driver via bot
        from driver_bot import send_driver_message
        message = f"✅ *Registration Submitted Successfully!*\n\n"
        message += f"📋 **Application Details:**\n"
        message += f"👤 Name: {name}\n"
        message += f"📞 Phone: {phone}\n"
        message += f"🚗 Vehicle: {vehicle_type}\n\n"
        message += f"📄 **Documents Uploaded:**\n"
        message += f"• Driver's License: {'✅' if 'license_front' in document_urls else '❌'}\n"
        message += f"• Government ID: {'✅' if 'id_front' in document_urls else '❌'}\n"
        message += f"• Vehicle Registration: {'✅' if 'vehicle_registration' in document_urls else '❌'}\n\n"
        message += f"⏳ **Status:** Pending Admin Approval\n"
        message += f"🔔 You'll receive a notification once approved!\n\n"
        message += f"📞 Contact support if you have any questions."
        
        send_driver_message(chat_id, message)
        
        # Notify admin
        from bot_minimal import send_message_to_admin
        from models import AdminUser
        admin_message = f"🚨 *New Driver Registration*\n\n"
        admin_message += f"👤 **Driver Details:**\n"
        admin_message += f"• Name: {name}\n"
        admin_message += f"• Phone: {phone}\n"
        admin_message += f"• Email: {email}\n"
        admin_message += f"• Vehicle: {vehicle_type}\n"
        admin_message += f"• Telegram ID: {chat_id}\n\n"
        admin_message += f"📄 **Documents:** {len(document_urls)} uploaded\n\n"
        admin_message += f"👆 **Action Required:** Please review and approve/reject this driver in the admin dashboard."
        
        admins = AdminUser.query.filter_by(is_active=True).all()
        for admin in admins:
            send_message_to_admin(admin.telegram_user_id, admin_message)
        
        return jsonify({'success': True, 'message': 'Registration submitted successfully!'})
        
    except Exception as e:
        logger.error(f"Error submitting driver registration: {e}")
        return jsonify({'success': False, 'error': 'Registration failed. Please try again.'}), 500

@app.route('/webapp')
def webapp():
    """Telegram WebApp page"""
    return render_template('webapp_modern_fixed.html')

@app.route('/admin')
def admin():
    """Admin dashboard"""
    return render_template('admin_simple_working.html')



@app.route('/enhanced-driver-panel')
def enhanced_driver_panel():
    """Enhanced driver panel with BeU delivery style"""
    return render_template('enhanced_driver_panel.html')

@app.route('/api/driver-registration-legacy', methods=['POST'])
def api_driver_registration_legacy():
    """API endpoint for driver registration"""
    try:
        # Check if request has JSON data or form data
        if request.is_json:
            data = request.get_json()
            telegram_id = data.get('telegram_id')
            name = data.get('name')
            phone_number = data.get('phone_number')
            vehicle_type = data.get('vehicle_type')
        else:
            # Safely handle form data with error catching
            try:
                telegram_id = request.form.get('telegram_id')
                name = request.form.get('name')
                phone_number = request.form.get('phone_number')
                vehicle_type = request.form.get('vehicle_type')
            except Exception as form_error:
                logger.error(f"Error parsing form data: {form_error}")
                return jsonify({'success': False, 'message': 'Invalid form data'}), 400
        
        if not all([telegram_id, name, phone_number]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Check if driver already exists
        existing_driver = Driver.query.filter_by(telegram_user_id=int(telegram_id)).first()
        if existing_driver:
            return jsonify({'success': False, 'message': 'Driver already registered'})
        
        # Create new driver with required fields
        driver = Driver(
            name=name,
            phone_number=phone_number, 
            telegram_user_id=int(telegram_id),
            vehicle_type=vehicle_type or "motorcycle",
            is_active=True,
            is_available=False,  # Not available until approved
            is_approved=False,
            approval_status='pending'
        )
        
        # Handle file uploads only if form data and files exist
        if not request.is_json:
            try:
                if request.files:
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
            except Exception as file_error:
                logger.warning(f"Error handling file uploads: {file_error}")
                # Continue registration without files
        
        db.session.add(driver)
        db.session.commit()
        
        # Send pending registration message
        try:
            from driver_registration import send_driver_registration_pending, notify_admin_driver_registration
            send_driver_registration_pending(int(telegram_id), name)
            
            # Notify admin
            notify_admin_driver_registration({
                'name': name,
                'phone_number': phone_number,
                'vehicle_type': vehicle_type,
                'documents_uploaded': bool(request.files) if not request.is_json else False
            })
        except Exception as notify_error:
            logger.error(f"Error sending notifications: {notify_error}")
        
        return jsonify({'success': True, 'message': 'Registration submitted successfully'})
        
    except Exception as e:
        logger.error(f"Error in driver registration: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 500

@app.route('/api/driver-registration-simple', methods=['POST'])
def api_driver_registration_simple():
    """Simple JSON-only driver registration endpoint"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'JSON data required'}), 400
            
        data = request.get_json()
        
        telegram_id = data.get('telegram_id')
        name = data.get('name')
        phone_number = data.get('phone_number')
        vehicle_type = data.get('vehicle_type', 'bicycle')
        
        if not all([telegram_id, name, phone_number]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Check if driver already exists
        existing_driver = Driver.query.filter_by(telegram_user_id=int(telegram_id)).first()
        if existing_driver:
            return jsonify({'success': False, 'message': 'Driver already registered'})
        
        # Create new driver
        driver = Driver(
            name=name,
            phone_number=phone_number, 
            telegram_user_id=int(telegram_id),
            vehicle_type=vehicle_type,
            is_active=True,
            is_available=False,
            is_approved=False,
            approval_status='pending'
        )
        
        db.session.add(driver)
        db.session.commit()
        
        # Send notifications
        try:
            from driver_registration import send_driver_registration_pending, notify_admin_driver_registration
            send_driver_registration_pending(int(telegram_id), name)
            
            notify_admin_driver_registration({
                'name': name,
                'phone_number': phone_number,
                'vehicle_type': vehicle_type,
                'documents_uploaded': False
            })
        except Exception as notify_error:
            logger.error(f"Error sending notifications: {notify_error}")
        
        return jsonify({'success': True, 'message': 'Registration submitted successfully'})
        
    except Exception as e:
        logger.error(f"Error in simple driver registration: {e}")
        db.session.rollback()
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

@app.route('/api/live-drivers')
def get_live_drivers():
    """Get drivers with live location data"""
    try:
        from live_driver_tracking import LiveDriverTracker
        tracker = LiveDriverTracker()
        live_drivers = tracker.get_live_drivers()
        
        return jsonify({
            'success': True,
            'drivers': live_drivers,
            'count': len(live_drivers),
            'last_update': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching live drivers: {e}")
        return jsonify({'error': 'Failed to fetch live drivers'}), 500

@app.route('/api/drivers/<int:driver_id>/location-request', methods=['POST'])
def api_request_driver_location(driver_id):
    """Request location from specific driver"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        if not driver.telegram_user_id:
            return jsonify({'success': False, 'message': 'Driver has no Telegram account linked'}), 400
        
        from live_driver_tracking import LiveDriverTracker
        tracker = LiveDriverTracker()
        success = tracker.request_location_from_driver(driver.telegram_user_id)
        
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
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/drivers/<int:driver_id>/live-location-request', methods=['POST'])
def api_request_driver_live_location(driver_id):
    """Request live location sharing from specific driver"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        if not driver.telegram_user_id:
            return jsonify({'success': False, 'message': 'Driver has no Telegram account linked'}), 400
        
        from live_driver_tracking import LiveDriverTracker
        tracker = LiveDriverTracker()
        success = tracker.request_live_location_from_driver(driver.telegram_user_id)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Live location request sent to {driver.name}'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to send live location request'
            }), 500
            
    except Exception as e:
        logger.error(f"Error requesting driver live location: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

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
        
        # Send real-time notification to admin only (no driver notification)
        from real_time_admin_system import notify_admin_new_order
        notify_admin_new_order(order.id)
        
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
        
        # Trigger driver notification when admin confirms order
        if new_status == 'confirmed' and old_status == 'pending':
            try:
                from complete_order_workflow import OrderWorkflowManager
                workflow_manager = OrderWorkflowManager()
                import threading
                
                def find_drivers_with_context():
                    """Function to run driver search with Flask app context"""
                    with app.app_context():
                        try:
                            success = workflow_manager.find_nearby_drivers(order_id)
                            if success:
                                logger.info(f"✅ Successfully notified drivers for order {order_id}")
                            else:
                                logger.warning(f"⚠️ No drivers found for order {order_id}")
                        except Exception as e:
                            logger.error(f"Error in driver search context: {e}")
                
                # Start driver search in background to avoid blocking the response
                threading.Thread(
                    target=find_drivers_with_context,
                    daemon=True
                ).start()
                logger.info(f"Driver search initiated for confirmed order {order_id}")
            except Exception as e:
                logger.error(f"Error initiating driver search for order {order_id}: {e}")
        
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

@app.route('/api/user-profile/<int:user_id>')
def get_user_profile(user_id):
    """Get user profile information including contact data from bot registration"""
    try:
        from models import UserProfile
        user_profile = UserProfile.query.filter_by(telegram_user_id=user_id).first()
        
        if user_profile:
            return jsonify({
                'success': True,
                'first_name': user_profile.first_name or '',
                'phone_number': user_profile.phone_number or '',
                'location_lat': user_profile.location_lat,
                'location_lng': user_profile.location_lng
            })
        else:
            return jsonify({
                'success': False,
                'message': 'User profile not found'
            })
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        return jsonify({'error': 'Failed to fetch user profile'}), 500

@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """Cancel an order - allows cancellation for pending, confirmed, and preparing orders"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Check if order can be cancelled
        cancellable_statuses = ['pending', 'confirmed', 'preparing']
        if order.status not in cancellable_statuses:
            return jsonify({
                'error': f'Order cannot be cancelled. Current status: {order.status}. Only orders with status {", ".join(cancellable_statuses)} can be cancelled.'
            }), 400
        
        # Update order status to cancelled
        old_status = order.status
        order.status = 'cancelled'
        order.updated_at = datetime.utcnow()
        
        # If order was assigned to a driver, unassign it
        if order.driver_id:
            order.driver_id = None
        
        db.session.commit()
        
        # Notify customer about cancellation
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, 'cancelled')
        except Exception as e:
            logger.error(f"Error notifying customer about cancellation: {e}")
        
        # Notify driver if order was assigned
        if old_status in ['confirmed', 'preparing']:
            try:
                from driver_bot import send_driver_message
                if order.driver_id:
                    send_driver_message(
                        order.driver_id,
                        f"⚠️ Order #{order_id} has been cancelled by the customer."
                    )
            except Exception as e:
                logger.error(f"Error notifying driver about cancellation: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} has been cancelled successfully',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': 'cancelled'
        })
    
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel order'}), 500

@app.route('/api/orders/<int:order_id>/delete', methods=['DELETE'])
def delete_order(order_id):
    """Delete a specific order permanently"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Store order details for logging
        order_info = f"Order #{order.id} - {order.customer_name}"
        
        db.session.delete(order)
        db.session.commit()
        
        logger.info(f"Order deleted: {order_info}")
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting order {order_id}: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete order'}), 500

@app.route('/api/orders/clear', methods=['DELETE'])
def clear_orders():
    """Clear orders by date range"""
    try:
        data = request.get_json()
        clear_type = data.get('type', 'all')  # all, day, week, month, year
        reference_date = data.get('date')  # ISO date string
        
        if reference_date:
            ref_date = datetime.fromisoformat(reference_date.replace('Z', '+00:00'))
        else:
            ref_date = datetime.utcnow()
        
        # Calculate date range based on clear_type
        if clear_type == 'day':
            start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif clear_type == 'week':
            # Get start of week (Monday)
            days_since_monday = ref_date.weekday()
            start_date = (ref_date - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(weeks=1)
        elif clear_type == 'month':
            start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if ref_date.month == 12:
                end_date = start_date.replace(year=ref_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=ref_date.month + 1)
        elif clear_type == 'year':
            start_date = ref_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date.replace(year=ref_date.year + 1)
        else:  # 'all'
            start_date = datetime(1970, 1, 1)
            end_date = datetime.utcnow() + timedelta(days=1)
        
        # Find orders in the date range
        orders_to_delete = Order.query.filter(
            Order.created_at >= start_date,
            Order.created_at < end_date
        ).all()
        
        count = len(orders_to_delete)
        
        if count == 0:
            return jsonify({
                'success': True,
                'message': f'No orders found in the specified {clear_type} range',
                'deleted_count': 0
            })
        
        # Delete the orders
        for order in orders_to_delete:
            db.session.delete(order)
        
        db.session.commit()
        
        logger.info(f"Bulk deleted {count} orders from {clear_type} range: {start_date} to {end_date}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {count} orders from {clear_type} range',
            'deleted_count': count,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'type': clear_type
            }
        })
        
    except Exception as e:
        logger.error(f"Error clearing orders: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to clear orders'}), 500

@app.route('/api/drivers/live-locations')
def get_drivers_live_locations():
    """Get all drivers with their live locations and status"""
    try:
        from datetime import datetime, timedelta
        
        drivers = Driver.query.filter_by(is_approved=True).all()
        drivers_data = []
        
        for driver in drivers:
            # Check if location is recent (within 10 minutes)
            location_active = False
            last_update_str = 'Never'
            
            if driver.last_location_update:
                time_diff = datetime.utcnow() - driver.last_location_update
                location_active = time_diff.total_seconds() < 600  # Less than 10 minutes
                last_update_str = driver.last_location_update.strftime('%H:%M:%S')
            
            # Determine overall status
            if not driver.is_active:
                status = 'Offline'
                status_color = '#6c757d'  # Gray
            elif not location_active:
                status = 'Location Outdated'
                status_color = '#dc3545'  # Red
            elif not driver.is_available:
                status = 'Busy'
                status_color = '#fd7e14'  # Orange
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
                'is_active': driver.is_active,
                'is_available': driver.is_available,
                'last_location_update': last_update_str,
                'location_active': location_active,
                'status': status,
                'status_color': status_color,
                'telegram_user_id': driver.telegram_user_id
            }
            drivers_data.append(driver_data)
        
        return jsonify({
            'success': True,
            'drivers': drivers_data,
            'total_drivers': len(drivers_data),
            'active_drivers': len([d for d in drivers_data if d['status'] == 'Available']),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching drivers live locations: {e}")
        return jsonify({'error': 'Failed to fetch driver locations'}), 500

@app.route('/api/drivers/<int:driver_id>/request-location', methods=['POST'])
def request_driver_location(driver_id):
    """Request driver to share current location"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        if not driver.telegram_user_id:
            return jsonify({'error': 'Driver has no Telegram account linked'}), 400
        
        # Send location request via driver bot
        from driver_bot import send_location_request
        send_location_request(driver.telegram_user_id)
        
        return jsonify({
            'success': True,
            'message': f'Location request sent to {driver.name}'
        })
        
    except Exception as e:
        logger.error(f"Error requesting driver location: {e}")
        return jsonify({'error': 'Failed to request driver location'}), 500

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
    """Add new menu item with file upload support"""
    try:
        # Handle both JSON and FormData
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData from modal
            name = request.form.get('name')
            price = float(request.form.get('price'))
            description = request.form.get('description', '')
            category = request.form.get('category')
            available = request.form.get('available') == 'on' or request.form.get('available') == 'true'
            image_url = request.form.get('image_url', '')
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = str(int(datetime.now().timestamp()))
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    image_url = f"/static/uploads/{filename}"
            
            # If no image uploaded and no URL provided, use default
            if not image_url:
                image_url = 'https://via.placeholder.com/300x200?text=Menu+Item'
        else:
            # JSON data (legacy support)
            data = request.get_json()
            name = data['name']
            price = float(data['price'])
            description = data.get('description', '')
            category = data.get('category', 'burgers')
            image_url = data.get('image_url', 'https://via.placeholder.com/300x200?text=Menu+Item')
            available = data.get('available', True)
        
        item = MenuItem(
            name=name,
            price=price,
            description=description,
            image_url=image_url,
            category=category,
            available=available
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Menu item added successfully', 'item_id': item.id}), 201
    
    except Exception as e:
        logger.error(f"Error adding menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to add menu item'}), 500

@app.route('/api/menu/<int:item_id>', methods=['GET'])
def get_menu_item(item_id):
    """Get single menu item"""
    try:
        item = MenuItem.query.get_or_404(item_id)
        return jsonify(item.to_dict())
    except Exception as e:
        logger.error(f"Error fetching menu item: {e}")
        return jsonify({'error': 'Failed to fetch menu item'}), 500

@app.route('/api/menu/<int:item_id>', methods=['PUT'])
def update_menu_item(item_id):
    """Update menu item with file upload support"""
    try:
        item = MenuItem.query.get_or_404(item_id)
        
        # Handle both JSON and FormData
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData from modal
            name = request.form.get('name')
            price = float(request.form.get('price'))
            description = request.form.get('description', '')
            category = request.form.get('category')
            available = request.form.get('available') == 'on' or request.form.get('available') == 'true'
            image_url = request.form.get('image_url', item.image_url)
            
            # Handle image upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = str(int(datetime.now().timestamp()))
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    image_url = f"/static/uploads/{filename}"
        else:
            # JSON data (legacy support)
            data = request.get_json()
            name = data.get('name', item.name)
            price = float(data.get('price', item.price))
            description = data.get('description', item.description)
            category = data.get('category', item.category)
            image_url = data.get('image_url', item.image_url)
            available = data.get('available', item.available)
        
        # Update item fields
        if name:
            item.name = name
        if price:
            item.price = price
        if description:
            item.description = description
        if category:
            item.category = category
        if image_url:
            item.image_url = image_url
        item.available = available
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Menu item updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update menu item'}), 500

@app.route('/api/menu/<int:item_id>', methods=['DELETE'])
def delete_menu_item(item_id):
    """Delete menu item"""
    try:
        item = MenuItem.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Menu item deleted successfully'})
    
    except Exception as e:
        logger.error(f"Error deleting menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to delete menu item'}), 500

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
        driver = Driver.query.get(driver_id)
        if not driver:
            return jsonify({'success': False, 'message': 'Driver not found'}), 404
            
        if driver.approval_status != 'pending':
            return jsonify({'success': False, 'message': f'Driver is already {driver.approval_status}'}), 400
            
        # Update driver status
        driver.approval_status = 'approved'
        driver.is_approved = True
        driver.is_available = True
        driver.approved_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send approval notification to driver with inline buttons
        if driver.telegram_user_id:
            try:
                from admin_approval_system import send_driver_approval_notification
                send_driver_approval_notification(driver.telegram_user_id, driver.name)
            except Exception as e:
                logger.error(f"Failed to send approval notification: {e}")
        
        return jsonify({'success': True, 'message': f'Driver {driver.name} approved successfully'})
        
    except Exception as e:
        logger.error(f"Error approving driver: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to approve driver'}), 500

@app.route('/api/drivers/<int:driver_id>/reject', methods=['POST'])
def reject_driver_api(driver_id):
    """Reject a pending driver"""
    try:
        driver = Driver.query.get(driver_id)
        if not driver:
            return jsonify({'success': False, 'message': 'Driver not found'}), 404
            
        if driver.approval_status != 'pending':
            return jsonify({'success': False, 'message': f'Driver is already {driver.approval_status}'}), 400
            
        data = request.get_json()
        reason = data.get('reason', 'Application does not meet requirements')
        
        # Update driver status
        driver.approval_status = 'rejected'
        driver.is_approved = False
        driver.is_available = False
        driver.rejection_reason = reason
        driver.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send rejection notification to driver
        if driver.telegram_user_id:
            try:
                from driver_bot import send_driver_message
                rejection_message = f"""
❌ *Registration Update*

Unfortunately, your driver registration has been declined.

*Reason:* {reason}

📞 If you have questions, please contact our support team.
🔄 You can reapply after addressing the concerns mentioned above.

Contact admin for more information.
"""
                send_driver_message(driver.telegram_user_id, rejection_message)
            except Exception as e:
                logger.error(f"Failed to send rejection notification: {e}")
        
        return jsonify({'success': True, 'message': f'Driver {driver.name} rejected successfully'})
        
    except Exception as e:
        logger.error(f"Error rejecting driver: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to reject driver'}), 500



@app.route('/api/drivers/add-employee', methods=['POST'])
def add_driver_employee():
    """Add a new driver employee with enhanced features"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'phone_number', 'vehicle_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Format phone number
        phone_number = data.get('phone_number', '').strip()
        if not phone_number.startswith('+'):
            phone_number = '+251' + phone_number.lstrip('+251')
        
        # Check if phone number already exists
        existing_driver = Driver.query.filter_by(phone_number=phone_number).first()
        if existing_driver:
            return jsonify({'success': False, 'message': 'Driver with this phone number already exists'}), 400
        
        # Check if Telegram ID already exists (if provided)
        telegram_id = data.get('telegram_user_id')
        if telegram_id:
            existing_telegram = Driver.query.filter_by(telegram_user_id=telegram_id).first()
            if existing_telegram:
                return jsonify({'success': False, 'message': 'Driver with this Telegram ID already exists'}), 400
        
        # Create new driver
        auto_approve = data.get('auto_approve', False)
        driver = Driver(
            name=data['name'],
            phone_number=phone_number,
            telegram_user_id=telegram_id if telegram_id else None,
            vehicle_type=data['vehicle_type'],
            is_active=True,
            is_available=auto_approve,
            is_approved=auto_approve,
            approval_status='approved' if auto_approve else 'pending',
            approved_at=datetime.utcnow() if auto_approve else None
        )
        
        db.session.add(driver)
        db.session.commit()
        
        # Send welcome message to driver if Telegram ID provided
        if telegram_id:
            try:
                from driver_bot import send_driver_message
                if auto_approve:
                    welcome_message = f"""
🎉 *Welcome to ET-FOOD Delivery Team!*

Hello {driver.name}! You've been added as a delivery driver.

✅ Your account has been automatically approved.
🚗 Vehicle Type: {driver.vehicle_type}
📱 Phone: {driver.phone_number}

📱 *Driver Commands:*
• /status - Check your status
• /orders - View your orders  
• /location - Share current location
• /toggle - Toggle availability

📍 Share your location to start receiving delivery requests!
"""
                else:
                    welcome_message = f"""
👋 *Welcome to ET-FOOD!*

Hello {driver.name}! You've been added as a driver employee.

📋 Your registration is pending admin approval.
🚗 Vehicle Type: {driver.vehicle_type}
📱 Phone: {driver.phone_number}

Please wait for admin approval to start receiving delivery requests.
"""
                
                send_driver_message(telegram_id, welcome_message)
            except Exception as e:
                logger.warning(f"Could not send welcome message to driver: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Driver {driver.name} added successfully',
            'driver_id': driver.id,
            'auto_approved': auto_approve
        })
        
    except Exception as e:
        logger.error(f"Error adding driver employee: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to add driver employee'}), 500

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

@app.route('/api/orders/<int:order_id>/assign-driver', methods=['PUT'])
def assign_driver_to_order(order_id):
    """Manually assign a driver to an order"""
    try:
        data = request.get_json()
        driver_id = data.get('driver_id')
        
        if not driver_id:
            return jsonify({'success': False, 'message': 'Driver ID is required'}), 400
        
        # Get order and driver
        order = Order.query.get_or_404(order_id)
        driver = Driver.query.get_or_404(driver_id)
        
        # Check if driver is available
        if not driver.is_active or not driver.is_available or not driver.is_approved:
            return jsonify({
                'success': False, 
                'message': 'Driver is not available for assignment'
            }), 400
        
        # Check if order is in correct status
        if order.status not in ['pending', 'confirmed']:
            return jsonify({
                'success': False, 
                'message': f'Order status "{order.status}" cannot be assigned to driver'
            }), 400
        
        # Assign driver
        order.driver_id = driver_id
        order.status = 'preparing'  # Update status to preparing
        order.updated_at = datetime.utcnow()
        
        # Make driver unavailable
        driver.is_available = False
        
        db.session.commit()
        
        # Notify driver about assignment
        try:
            from driver_bot import send_driver_message
            message = f"🚚 *ORDER ASSIGNED TO YOU*\n\n"
            message += f"📋 Order #{order.id}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"🏠 Address: {order.customer_address}\n"
            message += f"💰 Amount: {order.total_amount:.2f} ETB\n"
            message += f"💳 Payment: {order.payment_method}\n\n"
            message += f"*Please proceed to restaurant for pickup*"
            
            send_driver_message(driver.telegram_user_id, message)
        except Exception as e:
            logger.warning(f"Could not notify driver about assignment: {e}")
        
        # Notify customer about driver assignment
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, 'preparing')
        except Exception as e:
            logger.warning(f"Could not notify customer about assignment: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Driver {driver.name} assigned to Order #{order_id}',
            'driver_name': driver.name,
            'driver_phone': driver.phone_number
        })
        
    except Exception as e:
        logger.error(f"Error assigning driver to order: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to assign driver'}), 500

@app.route('/api/orders/<int:order_id>/find-nearby-drivers', methods=['POST'])
def find_nearby_drivers_for_order(order_id):
    """Find and notify nearby drivers for an order"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Check if order is in correct status
        if order.status not in ['pending', 'confirmed']:
            return jsonify({
                'success': False, 
                'message': f'Order status "{order.status}" cannot be processed for driver assignment'
            }), 400
        
        # Use the existing nearby driver system
        from complete_order_workflow import OrderWorkflowManager
        manager = OrderWorkflowManager()
        
        # Update order status to confirmed if pending
        if order.status == 'pending':
            order.status = 'confirmed'
            order.updated_at = datetime.utcnow()
            db.session.commit()
        
        # Find nearby drivers
        success = manager.find_nearby_drivers(order_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Nearby drivers found and notified for Order #{order_id}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No nearby drivers available within 10km radius'
            })
        
    except Exception as e:
        logger.error(f"Error finding nearby drivers for order: {e}")
        return jsonify({'success': False, 'message': 'Failed to find nearby drivers'}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Create new category with file upload support"""
    try:
        # Handle both JSON and FormData
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData from modal
            name = request.form.get('name')
            description = request.form.get('description', '')
            icon = request.form.get('icon', '🍽️')
            sort_order = int(request.form.get('sort_order', 0))
            
            # Handle image upload
            image_url = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = str(int(datetime.now().timestamp()))
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    image_url = f"/static/uploads/{filename}"
        else:
            # JSON data (legacy support)
            data = request.get_json()
            name = data['name']
            description = data.get('description', '')
            icon = data.get('icon', '🍽️')
            image_url = data.get('image_url')
            sort_order = data.get('sort_order', 0)
        
        category = Category(
            name=name,
            description=description,
            icon=icon,
            image_url=image_url,
            sort_order=sort_order
        )
        db.session.add(category)
        db.session.commit()
        
        return jsonify({'success': True, 'category_id': category.id})
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to create category'}), 500

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

# Duplicate route removed - using /api/orders/<int:order_id>/assign-driver instead

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

@app.route('/api/test-driver-notification', methods=['POST'])
def test_driver_notification():
    """Test notification to specific driver"""
    try:
        data = request.get_json()
        driver_id = data.get('driver_id')
        message = data.get('message', 'Test notification from admin')
        
        if not driver_id:
            return jsonify({'error': 'driver_id is required'}), 400
        
        # Get driver from database
        driver = Driver.query.get(driver_id)
        if not driver:
            return jsonify({'error': 'Driver not found'}), 404
        
        if not driver.telegram_user_id:
            return jsonify({'error': 'Driver has no Telegram ID'}), 400
        
        # Send test notification
        from driver_bot import send_driver_message
        
        test_message = f"""
🔔 *Test Notification*

Hello {driver.name}! This is a test message from the admin.

📋 *Your Info:*
• Name: {driver.name}
• Phone: {driver.phone_number}
• Vehicle: {driver.vehicle_type}
• Status: {'Active' if driver.is_active else 'Inactive'}

{message}

📱 If you can read this, your driver bot is working properly!
"""
        
        success = send_driver_message(driver.telegram_user_id, test_message)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Test notification sent to {driver.name}',
                'driver_telegram_id': driver.telegram_user_id
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to send notification to {driver.name}',
                'reason': 'Driver needs to start @Food_Driver_Bot first',
                'driver_telegram_id': driver.telegram_user_id,
                'instructions': f'Tell {driver.name} to start @Food_Driver_Bot on Telegram'
            })
        
    except Exception as e:
        logger.error(f"Error testing driver notification: {e}")
        return jsonify({'error': 'Failed to test driver notification'}), 500

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
        
        # Send approval notification via driver bot with inline buttons
        if driver.telegram_user_id:
            try:
                from admin_approval_system import send_driver_approval_notification
                send_driver_approval_notification(driver.telegram_user_id, driver.name)
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

@app.route('/api/drivers/<int:driver_id>/documents', methods=['GET'])
def get_driver_documents(driver_id):
    """Get driver documents"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        documents = {
            'driver_id': driver.id,
            'driver_name': driver.name,
            'license_document': driver.license_document,
            'id_document': driver.id_document,
            'vehicle_document': driver.vehicle_document,
            'license_front': None,
            'license_back': None,
            'id_front': None,
            'id_back': None,
            'vehicle_registration': None
        }
        
        # Check for specific document types in static/driver_documents folder
        import os
        from pathlib import Path
        
        driver_docs_folder = Path('static/driver_documents')
        if driver_docs_folder.exists():
            for file in driver_docs_folder.iterdir():
                if file.is_file() and str(driver.telegram_user_id) in file.name:
                    filename = file.name.lower()
                    if 'license' in filename:
                        if 'front' in filename:
                            documents['license_front'] = f'/static/driver_documents/{file.name}'
                        elif 'back' in filename:
                            documents['license_back'] = f'/static/driver_documents/{file.name}'
                        else:
                            documents['license_document'] = f'/static/driver_documents/{file.name}'
                    elif 'id' in filename:
                        if 'front' in filename:
                            documents['id_front'] = f'/static/driver_documents/{file.name}'
                        elif 'back' in filename:
                            documents['id_back'] = f'/static/driver_documents/{file.name}'
                        else:
                            documents['id_document'] = f'/static/driver_documents/{file.name}'
                    elif 'vehicle' in filename or 'reg' in filename:
                        documents['vehicle_registration'] = f'/static/driver_documents/{file.name}'
        
        return jsonify({
            'success': True,
            'documents': documents
        })
    except Exception as e:
        logger.error(f"Error fetching driver documents: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/drivers/<int:driver_id>', methods=['DELETE'])
def delete_driver(driver_id):
    """Delete a driver"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        
        # First, unassign any active orders
        active_orders = Order.query.filter_by(driver_id=driver_id).filter(
            Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
        ).all()
        
        for order in active_orders:
            order.driver_id = None
            order.status = 'confirmed'  # Reset to confirmed so admin can reassign
            
        # Delete the driver
        db.session.delete(driver)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Driver {driver.name} deleted successfully',
            'unassigned_orders': len(active_orders)
        })
    except Exception as e:
        logger.error(f"Error deleting driver: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Manual Driver Assignment Endpoints
@app.route('/api/orders/<int:order_id>/manual-assign-driver', methods=['POST'])
def manual_assign_driver_to_order(order_id):
    """Manually assign a specific driver to an order"""
    try:
        data = request.get_json()
        driver_id = data.get('driver_id')
        
        if not driver_id:
            return jsonify({'error': 'Driver ID is required'}), 400
        
        from manual_driver_assignment import manually_assign_driver
        
        # Get admin telegram ID from request (optional)
        admin_telegram_id = data.get('admin_telegram_id')
        
        result = manually_assign_driver(order_id, driver_id, admin_telegram_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Error manually assigning driver to order {order_id}: {e}")
        return jsonify({'error': 'Failed to assign driver'}), 500

@app.route('/api/orders/<int:order_id>/available-drivers', methods=['GET'])
def get_available_drivers_for_order(order_id):
    """Get list of available drivers for manual assignment"""
    try:
        from manual_driver_assignment import get_available_drivers_for_order
        
        drivers = get_available_drivers_for_order(order_id)
        
        return jsonify({
            'success': True,
            'drivers': drivers,
            'count': len(drivers)
        })
        
    except Exception as e:
        logger.error(f"Error getting available drivers for order {order_id}: {e}")
        return jsonify({'error': 'Failed to get available drivers'}), 500


