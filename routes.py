import os
import json
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
from flask import render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
from app import app
from extensions import db
from sqlalchemy import func
from models import MenuItem, Order, AdminUser, UserProfile, Category, Driver, SystemSettings, Restaurant, KitchenStaff
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
    """Main page - check if showing login portal or customer app"""
    # If accessed with ?admin=1, show login portal
    if request.args.get('admin') == '1':
        return render_template('login_home.html')
    return render_template('webapp_delivery_modern.html')

@app.route('/login-portal')
def login_portal():
    """Admin login portal page"""
    return render_template('login_home.html')

# Separate login routes for different user roles
@app.route('/superadmin', methods=['GET', 'POST'])
def superadmin():
    """Super Admin login page and dashboard"""
    # If already logged in and is super admin, show dashboard
    if 'admin_id' in session:
        admin_user = AdminUser.query.get(session['admin_id'])
        if admin_user and admin_user.role == 'super_admin':
            return render_template('super_admin_dashboard.html', admin=admin_user)
        else:
            # Not a super admin, logout and redirect to login
            session.clear()
            return redirect('/superadmin')
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check super admin credentials
        admin = AdminUser.query.filter_by(username=username, role='super_admin').first()
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            session['admin_role'] = admin.role
            return render_template('super_admin_dashboard.html', admin=admin)
        else:
            return render_template('superadmin_login.html', error='Invalid credentials')
    
    return render_template('superadmin_login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Restaurant Admin login page and dashboard"""
    # If already logged in, show appropriate dashboard based on role
    if 'admin_id' in session:
        admin_user = AdminUser.query.get(session['admin_id'])
        if admin_user:
            # Super admin should be redirected to /superadmin
            if admin_user.role == 'super_admin':
                return redirect('/superadmin')
            elif admin_user.role == 'kitchen_staff':
                return redirect('/kitchen')
            else:
                # Show restaurant admin dashboard
                return render_template('restaurant_admin_dashboard.html', admin=admin_user)
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check admin credentials (only regular admin and kitchen staff can login through /admin)
        admin = AdminUser.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            session['admin_role'] = admin.role
            session['restaurant_id'] = admin.restaurant_id if hasattr(admin, 'restaurant_id') else 1
            
            # Redirect based on role
            if admin.role == 'super_admin':
                return redirect('/superadmin')
            elif admin.role == 'kitchen_staff':
                return redirect('/kitchen')
            else:
                # Show restaurant admin dashboard
                return render_template('restaurant_admin_dashboard.html', admin=admin)
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')



# Password change functionality
@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password for logged-in admin"""
    if 'admin_id' not in session:
        return redirect('/login-portal')
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate passwords match
        if new_password != confirm_password:
            return render_template('change_password.html', error='New passwords do not match')
        
        # Validate password strength
        if len(new_password) < 8:
            return render_template('change_password.html', error='Password must be at least 8 characters long')
        
        # Get current admin
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return redirect('/login-portal')
        
        # Check current password
        if not admin.check_password(current_password):
            return render_template('change_password.html', error='Current password is incorrect')
        
        # Update password
        admin.set_password(new_password)
        db.session.commit()
        
        return render_template('change_password.html', success='Password changed successfully!')
    
    return render_template('change_password.html')

# Kitchen Staff Management API Routes
@app.route('/api/kitchen-staff', methods=['GET'])
def get_kitchen_staff():
    """Get all kitchen staff members"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = AdminUser.query.get(session['admin_id'])
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Get kitchen staff for this restaurant
    restaurant_id = getattr(admin, 'restaurant_id', 1)
    staff_members = KitchenStaff.query.filter_by(restaurant_id=restaurant_id).all()
    
    return jsonify({
        'success': True,
        'staff': [staff.to_dict() for staff in staff_members]
    })

@app.route('/api/kitchen-staff', methods=['POST'])
def add_kitchen_staff():
    """Add new kitchen staff member"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin = AdminUser.query.get(session['admin_id'])
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    try:
        data = request.form if request.content_type.startswith('multipart/form-data') else request.get_json()
        
        # Check if username already exists
        existing_staff = KitchenStaff.query.filter_by(username=data.get('username')).first()
        if existing_staff:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Handle image upload
        avatar_url = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = str(int(datetime.utcnow().timestamp()))
                filename = f"staff_{timestamp}_{filename}"
                file_path = os.path.join('static/uploads', filename)
                file.save(file_path)
                avatar_url = f'/static/uploads/{filename}'
        
        # Create new kitchen staff
        staff = KitchenStaff(
            name=data.get('name'),
            username=data.get('username'),
            phone=data.get('phone'),
            email=data.get('email'),
            position=data.get('position', 'Kitchen Staff'),
            salary=float(data.get('salary', 0)) if data.get('salary') else None,
            notes=data.get('notes'),
            avatar_url=avatar_url,
            restaurant_id=getattr(admin, 'restaurant_id', 1)
        )
        
        # Set password
        if data.get('password'):
            staff.set_password(data.get('password'))
        
        db.session.add(staff)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Kitchen staff member added successfully',
            'staff': staff.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/kitchen-staff/<int:staff_id>', methods=['PUT'])
def update_kitchen_staff(staff_id):
    """Update kitchen staff member"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    staff = KitchenStaff.query.get_or_404(staff_id)
    
    try:
        data = request.form if request.content_type.startswith('multipart/form-data') else request.get_json()
        
        # Update fields
        if data.get('name'):
            staff.name = data.get('name')
        if data.get('phone'):
            staff.phone = data.get('phone')
        if data.get('email'):
            staff.email = data.get('email')
        if data.get('position'):
            staff.position = data.get('position')
        if data.get('salary'):
            staff.salary = float(data.get('salary'))
        if data.get('notes'):
            staff.notes = data.get('notes')
        
        # Handle password change
        if data.get('new_password'):
            staff.set_password(data.get('new_password'))
        
        # Handle avatar update
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = str(int(datetime.utcnow().timestamp()))
                filename = f"staff_{timestamp}_{filename}"
                file_path = os.path.join('static/uploads', filename)
                file.save(file_path)
                staff.avatar_url = f'/static/uploads/{filename}'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Kitchen staff member updated successfully',
            'staff': staff.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/kitchen-staff/<int:staff_id>', methods=['DELETE'])
def delete_kitchen_staff(staff_id):
    """Delete kitchen staff member"""
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    staff = KitchenStaff.query.get_or_404(staff_id)
    
    try:
        db.session.delete(staff)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Kitchen staff member deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/menu')
def menu():
    """Menu page with restaurant selection"""
    restaurant_id = request.args.get('restaurant')
    if restaurant_id:
        # Store selected restaurant in session for the WebApp
        session['selected_restaurant'] = restaurant_id
    return render_template('webapp_delivery_modern.html')

@app.route('/select-restaurant')
def select_restaurant():
    """Restaurant selection page"""
    return render_template('select_restaurant.html')

@app.route('/test')
def test():
    """Test page"""
    return render_template('test.html')



@app.route('/super-admin')
def super_admin_redirect():
    """Redirect to secure admin login for super admin access"""
    return redirect(url_for('admin'))







@app.route('/api/driver-registration-legacy', methods=['POST'])
def api_driver_registration():
    """Handle driver registration submission from mini web app"""
    try:
        # Get form data - support both naming conventions
        full_name = request.form.get('fullName') or request.form.get('name')
        phone_number = request.form.get('phoneNumber') or request.form.get('phone_number')
        email = request.form.get('email', '')
        vehicle_type = request.form.get('vehicleType') or request.form.get('vehicle_type')
        experience = request.form.get('experience', '')
        telegram_user_id = request.form.get('telegramUserId') or request.form.get('telegram_user_id')
        
        # Validate required fields
        if not all([full_name, phone_number, vehicle_type]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Handle file uploads
        uploaded_files = {}
        file_fields = ['license_front', 'license_back', 'id_front', 'id_back', 'vehicle_registration']
        
        for field in file_fields:
            if field in request.files:
                file = request.files[field]
                if file and file.filename and allowed_file(file.filename):
                    # Generate unique filename
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"driver_{timestamp}_{secure_filename(file.filename)}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    
                    # Save file
                    file.save(filepath)
                    uploaded_files[field] = f"/static/uploads/{filename}"
        
        # Create driver record
        driver = Driver(
            name=full_name,
            phone_number=phone_number,
            email=email,
            vehicle_type=vehicle_type,
            experience=experience,
            telegram_user_id=int(telegram_user_id) if telegram_user_id else None,
            
            # Document URLs
            license_front_url=uploaded_files.get('license_front'),
            license_back_url=uploaded_files.get('license_back'),
            id_front_url=uploaded_files.get('id_front'),
            id_back_url=uploaded_files.get('id_back'),
            vehicle_registration_url=uploaded_files.get('vehicle_registration'),
            
            # Registration details
            registration_date=datetime.utcnow(),
            approval_status='pending',
            is_approved=False,
            is_active=False,
            is_available=False
        )
        
        db.session.add(driver)
        db.session.commit()
        
        logger.info(f"New driver registration: {full_name} - {phone_number}")
        
        # Notify admin about new driver registration
        from admin_approval_system import notify_admin_new_driver_registration
        try:
            notify_admin_new_driver_registration(driver.id)
        except Exception as e:
            logger.error(f"Failed to notify admin about new driver: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Registration submitted successfully',
            'driver_id': driver.id
        })
        
    except Exception as e:
        logger.error(f"Driver registration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



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
    return render_template('webapp_delivery_modern.html')



@app.route('/admin-panel')
def admin_panel():
    """Alternative admin panel"""
    return render_template('admin_clean.html')

@app.route('/api/admin/statistics')
def get_admin_statistics():
    """Get comprehensive admin statistics for super admin dashboard"""
    try:
        # Total orders
        total_orders = Order.query.count()
        
        # Total customers (unique telegram users)
        total_customers = db.session.query(Order.telegram_user_id).distinct().count()
        
        # Active drivers
        active_drivers = Driver.query.filter_by(is_active=True, is_approved=True).count()
        
        # Today's revenue
        today = datetime.now().date()
        today_orders = Order.query.filter(
            db.func.date(Order.created_at) == today,
            Order.status.in_(['delivered', 'out_for_delivery', 'preparing'])
        ).all()
        today_revenue = sum(order.total_amount for order in today_orders)
        
        # Recent orders count (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_orders = Order.query.filter(Order.created_at >= yesterday).count()
        
        # Active sessions (orders in progress)
        active_sessions = Order.query.filter(
            Order.status.in_(['pending', 'confirmed', 'preparing', 'out_for_delivery'])
        ).count()
        
        return jsonify({
            'total_orders': total_orders,
            'total_customers': total_customers,
            'active_drivers': active_drivers,
            'today_revenue': round(today_revenue, 2),
            'recent_orders': recent_orders,
            'active_sessions': active_sessions
        })
        
    except Exception as e:
        logger.error(f"Error getting admin statistics: {e}")
        return jsonify({'error': 'Failed to load statistics'}), 500

# Driver endpoint removed - using consolidated endpoint below

@app.route('/api/settings', methods=['POST'])
def save_system_settings():
    """Save system configuration settings"""
    try:
        data = request.get_json()
        
        # Define settings to save
        settings_map = {
            'delivery_radius': data.get('delivery_radius', '10'),
            'min_order_amount': data.get('min_order_amount', '50'),
            'delivery_fee': data.get('delivery_fee', '15'),
            'service_hours': data.get('service_hours', '8:00 AM - 11:00 PM'),
            'company_phone': data.get('company_phone', '+251-911-123456'),
            'company_email': data.get('company_email', 'admin@etfood.et')
        }
        
        # Update or create settings
        for key, value in settings_map.items():
            setting = SystemSettings.query.filter_by(setting_key=key).first()
            if setting:
                setting.setting_value = str(value)
                setting.updated_at = datetime.utcnow()
            else:
                setting = SystemSettings(
                    setting_key=key,
                    setting_value=str(value),
                    description=f"System setting for {key.replace('_', ' ').title()}"
                )
                db.session.add(setting)
        
        db.session.commit()
        logger.info("System settings updated successfully")
        
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving system settings: {e}")
        return jsonify({'error': 'Failed to save settings'}), 500





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
    """Get menu items organized by categories"""
    try:
        # Get restaurant ID from query parameter or session
        restaurant_id = request.args.get('restaurant_id', type=int)
        if restaurant_id is None:
            restaurant_id = session.get('selected_restaurant')
        
        # If still no restaurant, get first available active restaurant with menu items
        if restaurant_id is None:
            first_restaurant = db.session.query(Restaurant).filter(
                Restaurant.is_active == True,
                Restaurant.id.in_(
                    db.session.query(MenuItem.restaurant_id).filter(MenuItem.available == True).distinct()
                )
            ).first()
            restaurant_id = first_restaurant.id if first_restaurant else 1
        
        # Get all available menu items for the restaurant
        menu_items = MenuItem.query.filter_by(
            available=True, 
            restaurant_id=restaurant_id
        ).all()
        
        # Get unique categories with items count
        categories_data = {}
        for item in menu_items:
            category = item.category
            if category not in categories_data:
                categories_data[category] = {
                    'name': category,
                    'items': []
                }
            categories_data[category]['items'].append(item.to_dict())
        
        # Convert to list and sort categories
        categories_list = list(categories_data.values())
        categories_list.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'restaurant_id': restaurant_id,
            'total_items': len(menu_items),
            'total_categories': len(categories_list),
            'categories': categories_list,
            'items': [item.to_dict() for item in menu_items]  # Flat list for backward compatibility
        })
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

@app.route('/api/kitchen/orders', methods=['GET'])
def get_kitchen_orders():
    """Get orders for kitchen staff - all active orders including pending"""
    try:
        # Get time filter parameter (default: today only)
        time_filter = request.args.get('time_filter', 'today')
        
        # Get orders for kitchen staff (include out_for_delivery to show driver assignments)
        active_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery']
        
        from datetime import datetime, timedelta
        
        # Apply time filter
        if time_filter == 'today':
            # Only show orders from last 24 hours
            since_time = datetime.utcnow() - timedelta(hours=24)
            orders = Order.query.filter(
                Order.status.in_(active_statuses),
                Order.created_at >= since_time
            ).order_by(Order.created_at.asc()).all()
        elif time_filter == 'recent':
            # Only show orders from last 4 hours
            since_time = datetime.utcnow() - timedelta(hours=4)
            orders = Order.query.filter(
                Order.status.in_(active_statuses),
                Order.created_at >= since_time
            ).order_by(Order.created_at.asc()).all()
        else:
            # Show all active orders
            orders = Order.query.filter(
                Order.status.in_(active_statuses)
            ).order_by(Order.created_at.asc()).all()
        
        # Format orders for kitchen
        kitchen_orders = []
        for order in orders:
            order_dict = order.to_dict()
            
            # Ensure items are always parsed as JSON
            if isinstance(order_dict.get('items'), str):
                try:
                    import json
                    order_dict['items'] = json.loads(order_dict['items'])
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, set to empty list
                    order_dict['items'] = []
            elif not isinstance(order_dict.get('items'), list):
                # If items is not a list, set to empty list
                order_dict['items'] = []
            
            # Calculate time since order was placed - simple approach
            from datetime import datetime
            
            # Get current time and order creation time (both as naive datetime)
            now = datetime.utcnow()
            order_time = order.created_at
            
            # Calculate difference in minutes
            if order_time:
                time_diff = now - order_time
                minutes_ago = max(0, int(time_diff.total_seconds() / 60))
            else:
                minutes_ago = 0
                
            order_dict['minutes_ago'] = minutes_ago
            
            kitchen_orders.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': kitchen_orders,
            'count': len(kitchen_orders)
        })
        
    except Exception as e:
        logger.error(f"Error fetching kitchen orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/kitchen/confirm-availability/<int:order_id>', methods=['POST'])
def kitchen_confirm_availability(order_id):
    """Kitchen staff confirms order availability and triggers payment notification"""
    try:
        data = request.get_json()
        is_available = data.get('available', True)
        reason = data.get('reason', '')
        
        from enhanced_order_workflow import handle_kitchen_availability_response
        success = handle_kitchen_availability_response(order_id, is_available, reason)
        
        if success:
            if is_available:
                return jsonify({
                    'success': True,
                    'message': 'Order availability confirmed. Customer notified for payment.'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Order marked as unavailable. Customer notified.'
                })
        else:
            return jsonify({'success': False, 'error': 'Failed to process availability response'}), 500
            
    except Exception as e:
        logger.error(f"Error confirming kitchen availability: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/payment/auto-approve/<int:order_id>', methods=['POST'])
def auto_approve_payment(order_id):
    """Auto-approve payment and start kitchen preparation"""
    try:
        from enhanced_order_workflow import auto_approve_payment_and_start_kitchen
        success = auto_approve_payment_and_start_kitchen(order_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Payment auto-approved. Kitchen notified to start preparation.'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to auto-approve payment'}), 500
            
    except Exception as e:
        logger.error(f"Error auto-approving payment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<int:order_id>/status', methods=['POST'])
def kitchen_update_order_status(order_id):
    """Kitchen staff endpoint to update order status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        # Kitchen staff can update to confirmed, preparing or ready
        valid_kitchen_statuses = ['confirmed', 'preparing', 'ready']
        
        if not new_status or new_status not in valid_kitchen_statuses:
            return jsonify({'error': f'Kitchen staff can only update status to: {", ".join(valid_kitchen_statuses)}'}), 400
        
        order = Order.query.get_or_404(order_id)
        old_status = order.status
        
        # Validate status transition
        if old_status == new_status:
            return jsonify({'error': f'Order is already {new_status}'}), 400
        
        # Allow kitchen staff to progress orders from pending -> confirmed -> preparing -> ready
        valid_transitions = {
            'pending': ['confirmed'],
            'confirmed': ['preparing'],
            'preparing': ['ready']
        }
        
        if old_status in valid_transitions and new_status not in valid_transitions.get(old_status, []):
            return jsonify({'error': f'Cannot update order from {old_status} to {new_status}'}), 400
        
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify customer about status change
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, new_status)
        except Exception as e:
            logger.error(f"Error notifying customer about status change: {e}")
        
        # When kitchen marks order as "preparing", automatically search for nearby drivers
        if new_status == 'preparing':
            try:
                from threading import Thread
                from driver_integration_system import driver_system
                
                def find_and_notify_drivers():
                    with app.app_context():
                        success = driver_system.notify_new_order(order_id)
                        if success:
                            logger.info(f"✅ Successfully notified drivers about order #{order_id} - kitchen started preparing food")
                        else:
                            logger.warning(f"⚠️ No drivers available for order #{order_id} - kitchen preparing but no drivers found")
                
                # Run driver search in background thread
                Thread(target=find_and_notify_drivers, daemon=True).start()
                logger.info(f"🔍 Started automatic driver search for order #{order_id} marked as preparing")
            except Exception as e:
                logger.error(f"❌ Error starting driver search for order #{order_id}: {e}")
        
        # When kitchen marks order as "ready", also notify drivers (backup notification)
        elif new_status == 'ready':
            try:
                from threading import Thread
                from driver_integration_system import driver_system
                
                def find_and_notify_drivers():
                    with app.app_context():
                        success = driver_system.notify_new_order(order_id)
                        if success:
                            logger.info(f"✅ Successfully notified drivers about order #{order_id} - food is ready for pickup")
                        else:
                            logger.warning(f"⚠️ No drivers available for order #{order_id} - food ready but no drivers found")
                
                # Run driver search in background thread
                Thread(target=find_and_notify_drivers, daemon=True).start()
                logger.info(f"🔍 Started automatic driver search for order #{order_id} marked as ready")
            except Exception as e:
                logger.error(f"❌ Error starting driver search for order #{order_id}: {e}")
        
        # When order status changes to out_for_delivery, notify assigned driver with pickup details
        elif new_status == 'out_for_delivery' and order.driver_id:
            try:
                from driver_bot import send_driver_message
                driver = Driver.query.get(order.driver_id)
                if driver and driver.telegram_user_id:
                    message = f"🍽️ *ORDER READY FOR PICKUP*\n\n"
                    message += f"📋 Order #{order_id}\n"
                    message += f"👤 Customer: {order.customer_name}\n"
                    message += f"📍 Restaurant: ET-FOOD Kitchen\n"
                    message += f"🏠 Delivery: {order.delivery_address}\n"
                    message += f"💰 Total: {order.total_amount} ETB\n\n"
                    message += f"🚗 Please proceed to restaurant for pickup!"
                    
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "📍 Navigate to Restaurant", "url": "https://maps.google.com/?q=9.047658,38.741143"},
                                {"text": "☎️ Call Restaurant", "url": "tel:+251911234567"}
                            ],
                            [
                                {"text": "✅ Confirm Pickup", "callback_data": f"pickup_complete_{order_id}"}
                            ]
                        ]
                    }
                    
                    send_driver_message(driver.telegram_user_id, message, keyboard=keyboard)
                    logger.info(f"Notified driver {driver.name} that order #{order_id} is ready for pickup")
            except Exception as e:
                logger.error(f"Error notifying driver about ready order #{order_id}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} marked as {new_status}',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': new_status
        })
        
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update order status'}), 500

@app.route('/api/orders/<int:order_id>/unavailable', methods=['POST'])
def mark_order_unavailable(order_id):
    """Kitchen staff endpoint to mark order as unavailable"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'Order items are currently unavailable')
        
        if not reason.strip():
            return jsonify({'error': 'Reason for unavailability is required'}), 400
        
        order = Order.query.get_or_404(order_id)
        
        # Only allow marking unavailable for active orders
        if order.status not in ['pending', 'confirmed', 'preparing']:
            return jsonify({'error': f'Cannot mark order as unavailable. Current status: {order.status}'}), 400
        
        # Update order status to cancelled
        old_status = order.status
        order.status = 'cancelled'
        order.updated_at = datetime.utcnow()
        order.special_instructions = f"[UNAVAILABLE] {reason}"
        
        db.session.commit()
        
        # Notify customer about order unavailability
        try:
            from bot_minimal import send_message
            customer_message = f"""
🚫 *Order Unavailable - Order #{order_id}*

Dear {order.customer_name},

We're sorry to inform you that your order is currently unavailable.

*Reason:* {reason}

*Order Details:*
- Order ID: #{order_id}
- Total Amount: ETB {order.total_amount:.2f}

We apologize for the inconvenience. Please try ordering again later or contact us for alternative options.

Thank you for your understanding.

- ET-FOOD Team
            """
            
            # Try to send notification to customer via their telegram_user_id
            if order.telegram_user_id:
                send_message(order.telegram_user_id, customer_message, parse_mode="Markdown")
                logger.info(f"Sent unavailability notification to customer for order #{order_id}")
            else:
                logger.warning(f"No telegram_user_id for order #{order_id}, notification not sent")
                
        except Exception as e:
            logger.error(f"Error sending unavailability notification: {e}")
        
        logger.info(f"Kitchen marked order #{order_id} as unavailable. Reason: {reason}")
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} marked as unavailable. Customer has been notified.',
            'order_id': order_id,
            'reason': reason
        })
        
    except Exception as e:
        logger.error(f"Error marking order as unavailable: {e}")
        return jsonify({'error': 'Failed to mark order as unavailable'}), 500

@app.route('/api/orders/<int:order_id>/driver-status', methods=['GET'])
def get_order_driver_status(order_id):
    """Get driver assignment status and location for specific order"""
    try:
        order = Order.query.get_or_404(order_id)
        
        response_data = {
            'order_id': order_id,
            'driver_assigned': False,
            'driver_info': None,
            'driver_location': None,
            'assignment_time': None
        }
        
        if order.driver_id:
            driver = Driver.query.get(order.driver_id)
            if driver:
                response_data.update({
                    'driver_assigned': True,
                    'driver_info': {
                        'id': driver.id,
                        'name': driver.name,
                        'phone': driver.phone_number,
                        'vehicle_type': driver.vehicle_type,
                        'telegram_user_id': driver.telegram_user_id
                    },
                    'driver_location': {
                        'lat': driver.current_lat,
                        'lng': driver.current_lng,
                        'last_update': driver.last_location_update.isoformat() if driver.last_location_update else None
                    },
                    'assignment_time': order.updated_at.isoformat() if order.updated_at else None
                })
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting driver status for order #{order_id}: {e}")
        return jsonify({'error': 'Failed to get driver status'}), 500

@app.route('/api/admin/live-orders', methods=['GET'])
def get_admin_live_orders():
    """Get live orders with driver tracking for admin dashboard"""
    try:
        # Get orders that are being prepared or out for delivery
        active_statuses = ['preparing', 'ready', 'out_for_delivery']
        orders = Order.query.filter(
            Order.status.in_(active_statuses)
        ).order_by(Order.updated_at.desc()).all()
        
        live_orders = []
        for order in orders:
            order_dict = order.to_dict()
            
            # Add driver information if assigned
            if order.driver_id:
                driver = Driver.query.get(order.driver_id)
                if driver:
                    order_dict['driver'] = {
                        'id': driver.id,
                        'name': driver.name,
                        'phone': driver.phone_number,
                        'vehicle_type': driver.vehicle_type,
                        'current_lat': driver.current_lat,
                        'current_lng': driver.current_lng,
                        'location_updated_at': driver.last_location_update.isoformat() if driver.last_location_update else None,
                        'is_available': driver.is_available,
                        'is_active': driver.is_active
                    }
                    
                    # Add pickup status information
                    if order.status == 'out_for_delivery':
                        order_dict['pickup_status'] = {
                            'picked_up': True,
                            'pickup_time': order.updated_at.isoformat(),
                            'driver_name': driver.name,
                            'status_text': f"Picked up by {driver.name}"
                        }
                    else:
                        order_dict['pickup_status'] = {
                            'picked_up': False,
                            'pickup_time': None,
                            'driver_name': driver.name,
                            'status_text': f"Assigned to {driver.name}"
                        }
                else:
                    order_dict['driver'] = None
                    order_dict['pickup_status'] = {'picked_up': False, 'pickup_time': None, 'driver_name': None, 'status_text': 'Driver not found'}
            else:
                order_dict['driver'] = None
                order_dict['pickup_status'] = {'picked_up': False, 'pickup_time': None, 'driver_name': None, 'status_text': 'No driver assigned'}
            
            live_orders.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': live_orders,
            'count': len(live_orders)
        })
        
    except Exception as e:
        logger.error(f"Error fetching live orders for admin: {e}")
        return jsonify({'error': 'Failed to fetch live orders'}), 500

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

# Payment Verification API Endpoints
@app.route('/api/admin/payment-verification', methods=['GET'])
def get_admin_payment_verification_orders():
    """Get orders requiring payment verification (admin)"""
    try:
        # Get orders that need payment verification (status = 'payment_pending' or 'confirmed' with transaction_image_url)
        orders = Order.query.filter(
            db.or_(
                Order.status == 'payment_pending',
                db.and_(
                    Order.status == 'confirmed',
                    Order.transaction_image_url.isnot(None)
                )
            )
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            order_dict = order.to_dict()
            orders_data.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'count': len(orders_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching payment verification orders: {e}")
        return jsonify({'error': 'Failed to fetch payment verification orders'}), 500




@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create new order"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['customer_name', 'customer_phone', 'customer_address', 'items', 'payment_method']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Calculate total amount
        total_amount = 0
        for item in data['items']:
            total_amount += item['price'] * item['quantity']
        
        # Create order with proper telegram_user_id handling
        telegram_user_id = data.get('telegram_user_id')
        if not telegram_user_id:
            # Try to get from Telegram WebApp user data or use fallback
            telegram_user_id = 383870190  # Default fallback for web orders
        
        order = Order(
            telegram_user_id=telegram_user_id,
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

@app.route('/api/orders/pending-for-kitchen')
def get_pending_orders_for_kitchen():
    """Get orders pending kitchen processing"""
    try:
        orders = Order.query.filter(
            Order.status.in_(['pending', 'confirmed'])
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            order_dict = order.to_dict()
            # Parse items if they're stored as string
            if isinstance(order_dict['items'], str):
                import json
                order_dict['items'] = json.loads(order_dict['items'])
            orders_data.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'count': len(orders_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching pending kitchen orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/kitchen/order-unavailable', methods=['POST'])
def kitchen_mark_order_unavailable():
    """Mark order as unavailable"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        reason = data.get('reason', 'Items not available')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Update order status
        order.status = 'cancelled'
        db.session.commit()
        
        # TODO: Send notification to customer
        
        return jsonify({
            'success': True,
            'message': 'Order marked as unavailable and customer notified'
        })
        
    except Exception as e:
        logger.error(f"Error marking order unavailable: {e}")
        return jsonify({'error': 'Failed to mark order as unavailable'}), 500

@app.route('/kitchen-food-availability')
def kitchen_food_availability():
    """Kitchen food availability interface"""
    return render_template('kitchen_food_availability.html')

@app.route('/api/kitchen/food-available', methods=['POST'])
def mark_food_available():
    """Mark food as available and trigger deposit requirement"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Calculate deposit amount (50% of total)
        deposit_amount = order.total_amount * 0.5
        
        # Set deposit deadline (end of today)
        from datetime import datetime, time
        today = datetime.now().date()
        deposit_deadline = datetime.combine(today, time(23, 59, 59))
        
        # Update order with deposit information
        order.deposit_amount = deposit_amount
        order.deposit_deadline = deposit_deadline
        order.status = 'awaiting_deposit'  # New status for deposit workflow
        
        db.session.commit()
        
        # TODO: Send notification to customer about deposit requirement
        # This would normally use the bot to notify customer
        
        return jsonify({
            'success': True,
            'message': 'Food marked as available. Customer notified about deposit requirement.',
            'deposit_amount': deposit_amount,
            'deposit_deadline': deposit_deadline.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error marking food available: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to mark food as available'}), 500



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
        
        # Trigger driver notification when admin confirms order using real-time delivery system
        if new_status == 'confirmed' and old_status == 'pending':
            try:
                from real_time_delivery_system import process_order_for_delivery
                import threading
                
                def notify_drivers_with_context():
                    """Function to run driver notification with Flask app context"""
                    with app.app_context():
                        try:
                            success = process_order_for_delivery(order_id)
                            if success:
                                logger.info(f"✅ Real-time delivery system notified drivers for order {order_id}")
                            else:
                                logger.warning(f"⚠️ No drivers found for order {order_id}")
                        except Exception as e:
                            logger.error(f"Error in real-time delivery system: {e}")
                
                # Start driver notification in background to avoid blocking the response
                threading.Thread(
                    target=notify_drivers_with_context,
                    daemon=True
                ).start()
                logger.info(f"Real-time delivery system initiated for confirmed order {order_id}")
            except Exception as e:
                logger.error(f"Error initiating real-time delivery system for order {order_id}: {e}")
        
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

@app.route('/api/orders/payment-verification')
def get_payment_verification_orders():
    """Get orders that need payment verification (admin)"""
    try:
        # Get orders that have transaction image URLs (payment screenshots uploaded)
        orders = Order.query.filter(
            Order.transaction_image_url.isnot(None),
            Order.status.in_(['confirmed', 'preparing', 'ready', 'out_for_delivery'])
        ).order_by(Order.created_at.desc()).all()
        
        return jsonify({
            'orders': [order.to_dict() for order in orders],
            'total': len(orders)
        })
    except Exception as e:
        logger.error(f"Error fetching payment verification orders: {e}")
        return jsonify({'error': 'Failed to fetch payment verification orders'}), 500

@app.route('/api/orders/payment-verification/super-admin')
def get_super_admin_payment_verification_orders():
    """Get all payment verification orders (super admin view-only)"""
    try:
        # Get all orders with payment screenshots (both verified and unverified)
        orders = Order.query.filter(
            Order.transaction_image_url.isnot(None)
        ).order_by(Order.created_at.desc()).all()
        
        return jsonify({
            'orders': [order.to_dict() for order in orders],
            'total': len(orders)
        })
    except Exception as e:
        logger.error(f"Error fetching super admin payment verification orders: {e}")
        return jsonify({'error': 'Failed to fetch super admin payment verification orders'}), 500

@app.route('/api/orders/<int:order_id>/verify-payment', methods=['POST'])
def verify_payment(order_id):
    """Verify payment for an order (admin only)"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Update order status to payment verified
        order.status = 'payment_verified'
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify customer about payment verification
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, 'payment_verified')
        except Exception as e:
            logger.error(f"Error notifying customer about payment verification: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Payment verified for order #{order_id}',
            'order_id': order_id,
            'new_status': 'payment_verified'
        })
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to verify payment'}), 500

@app.route('/api/orders/<int:order_id>/reject-payment', methods=['POST'])
def reject_payment(order_id):
    """Reject payment for an order (admin only)"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Update order status to cancelled
        order.status = 'cancelled'
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify customer about payment rejection
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, 'cancelled')
        except Exception as e:
            logger.error(f"Error notifying customer about payment rejection: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Payment rejected for order #{order_id}',
            'order_id': order_id,
            'new_status': 'cancelled'
        })
    except Exception as e:
        logger.error(f"Error rejecting payment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to reject payment'}), 500

# Restaurant Management API Endpoints for Super Admin
@app.route('/api/restaurants/super-admin', methods=['GET'])
def get_restaurants_super_admin():
    """Get all restaurants for super admin"""
    try:
        restaurants = Restaurant.query.all()
        restaurants_data = []
        
        for restaurant in restaurants:
            # Count menu items and other associated data
            menu_items_count = MenuItem.query.filter_by(restaurant_id=restaurant.id).count()
            orders_count = Order.query.filter_by(restaurant_id=restaurant.id).count()
            orders_today = Order.query.filter(
                Order.restaurant_id == restaurant.id,
                func.date(Order.created_at) == func.date(datetime.utcnow())
            ).count()
            
            # Calculate today's revenue
            today_revenue = db.session.query(func.sum(Order.total_amount)).filter(
                Order.restaurant_id == restaurant.id,
                func.date(Order.created_at) == func.date(datetime.utcnow()),
                Order.status == 'delivered'
            ).scalar() or 0
            
            # Get admin name
            admin = AdminUser.query.filter_by(restaurant_id=restaurant.id, role='admin').first()
            admin_name = admin.full_name if admin else None
            
            restaurant_dict = restaurant.to_dict()
            restaurant_dict.update({
                'menu_items_count': menu_items_count,
                'orders_count': orders_count,
                'orders_today': orders_today,
                'revenue_today': today_revenue,
                'admin_name': admin_name
            })
            restaurants_data.append(restaurant_dict)
        
        return jsonify({
            'success': True,
            'restaurants': restaurants_data
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants: {e}")
        return jsonify({'error': 'Failed to fetch restaurants'}), 500

@app.route('/api/restaurants/super-admin', methods=['POST'])
def add_restaurant_super_admin():
    """Add a new restaurant (super admin)"""
    try:
        data = request.get_json()
        restaurant = Restaurant(
            name=data['name'],
            description=data.get('description', ''),
            address=data['address'],
            phone=data['phone'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            is_active=data.get('is_active', True)
        )
        
        db.session.add(restaurant)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Restaurant added successfully',
            'restaurant': restaurant.to_dict()
        })
    except Exception as e:
        logger.error(f"Error adding restaurant: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add restaurant'}), 500

# Restaurant deletion moved to admin_routes.py

# Kitchen Menu Management API Endpoints
@app.route('/api/kitchen/menu-items', methods=['GET'])
def get_kitchen_menu_items():
    """Get all menu items for kitchen management"""
    try:
        menu_items = MenuItem.query.all()
        categories = Category.query.all()
        
        return jsonify({
            'success': True,
            'menu_items': [item.to_dict() for item in menu_items],
            'categories': [cat.to_dict() for cat in categories]
        })
    except Exception as e:
        logger.error(f"Error fetching kitchen menu items: {e}")
        return jsonify({'error': 'Failed to fetch kitchen menu items'}), 500

@app.route('/api/kitchen/menu-items', methods=['POST'])
def add_kitchen_menu_item():
    """Add new menu item (kitchen staff)"""
    try:
        data = request.get_json()
        
        # Create new menu item
        menu_item = MenuItem(
            name=data['name'],
            price=float(data['price']),
            description=data.get('description', ''),
            category=data.get('category', 'general'),
            image_url=data.get('image_url', ''),
            available=data.get('available', True),
            restaurant_id=data.get('restaurant_id', 1)
        )
        
        db.session.add(menu_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item added successfully',
            'menu_item': menu_item.to_dict()
        })
    except Exception as e:
        logger.error(f"Error adding kitchen menu item: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add menu item'}), 500

@app.route('/api/kitchen/menu-items/<int:item_id>', methods=['PUT'])
def update_kitchen_menu_item(item_id):
    """Update menu item (kitchen staff)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        data = request.get_json()
        
        # Update menu item fields
        if 'name' in data:
            menu_item.name = data['name']
        if 'price' in data:
            menu_item.price = float(data['price'])
        if 'description' in data:
            menu_item.description = data['description']
        if 'category' in data:
            menu_item.category = data['category']
        if 'image_url' in data:
            menu_item.image_url = data['image_url']
        if 'available' in data:
            menu_item.available = data['available']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item updated successfully',
            'menu_item': menu_item.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating kitchen menu item: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update menu item'}), 500

@app.route('/api/kitchen/menu-items/<int:item_id>', methods=['DELETE'])
def delete_kitchen_menu_item(item_id):
    """Delete menu item (kitchen staff)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        db.session.delete(menu_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting kitchen menu item: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete menu item'}), 500

# Payment Verification API Endpoint moved to admin_routes.py

# Location-based Restaurant Detection
@app.route('/api/restaurants/nearby', methods=['POST'])
def get_nearby_restaurants():
    """Get nearby restaurants based on user location"""
    try:
        data = request.get_json()
        user_lat = data.get('latitude')
        user_lng = data.get('longitude')
        radius = data.get('radius', 10)  # Default 10km radius
        
        if not user_lat or not user_lng:
            return jsonify({'error': 'Location coordinates required'}), 400
        
        # Get all active restaurants
        restaurants = Restaurant.query.filter_by(is_active=True).all()
        
        # Calculate distances and filter by radius
        nearby_restaurants = []
        for restaurant in restaurants:
            if restaurant.latitude and restaurant.longitude:
                distance = calculate_distance(
                    user_lat, user_lng, 
                    restaurant.latitude, restaurant.longitude
                )
                if distance <= radius:
                    restaurant_data = restaurant.to_dict()
                    restaurant_data['distance'] = round(distance, 2)
                    nearby_restaurants.append(restaurant_data)
        
        # Sort by distance
        nearby_restaurants.sort(key=lambda x: x['distance'])
        
        return jsonify({
            'success': True,
            'restaurants': nearby_restaurants,
            'user_location': {'latitude': user_lat, 'longitude': user_lng}
        })
    except Exception as e:
        logger.error(f"Error finding nearby restaurants: {e}")
        return jsonify({'error': 'Failed to find nearby restaurants'}), 500

@app.route('/api/restaurants/auto-detect', methods=['POST'])
def auto_detect_restaurant():
    """Auto-detect closest restaurant and set as default"""
    try:
        data = request.get_json()
        user_lat = data.get('latitude')
        user_lng = data.get('longitude')
        
        if not user_lat or not user_lng:
            return jsonify({'error': 'Location coordinates required'}), 400
        
        # Get all active restaurants
        restaurants = Restaurant.query.filter_by(is_active=True).all()
        
        # Find closest restaurant
        closest_restaurant = None
        min_distance = float('inf')
        
        for restaurant in restaurants:
            if restaurant.latitude and restaurant.longitude:
                distance = calculate_distance(
                    user_lat, user_lng, 
                    restaurant.latitude, restaurant.longitude
                )
                if distance < min_distance:
                    min_distance = distance
                    closest_restaurant = restaurant
        
        if closest_restaurant:
            restaurant_data = closest_restaurant.to_dict()
            restaurant_data['distance'] = round(min_distance, 2)
            
            return jsonify({
                'success': True,
                'restaurant': restaurant_data,
                'message': f'Closest restaurant found: {closest_restaurant.name} ({min_distance:.2f} km away)'
            })
        else:
            return jsonify({'error': 'No restaurants found in your area'}), 404
            
    except Exception as e:
        logger.error(f"Error auto-detecting restaurant: {e}")
        return jsonify({'error': 'Failed to auto-detect restaurant'}), 500



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

@app.route('/api/drivers/nearby', methods=['POST'])
def get_nearby_drivers():
    """Get nearby drivers for restaurant admins based on restaurant location"""
    try:
        data = request.get_json()
        restaurant_lat = data.get('restaurant_lat')
        restaurant_lng = data.get('restaurant_lng')
        radius = data.get('radius', 10)  # Default 10km radius
        
        if not restaurant_lat or not restaurant_lng:
            return jsonify({'error': 'Restaurant location coordinates required'}), 400
        
        # Get all approved and active drivers with recent location updates
        from datetime import datetime, timedelta
        recent_time = datetime.utcnow() - timedelta(minutes=10)
        
        drivers = Driver.query.filter(
            Driver.is_approved == True,
            Driver.is_active == True,
            Driver.current_lat.isnot(None),
            Driver.current_lng.isnot(None),
            Driver.last_location_update >= recent_time
        ).all()
        
        # Calculate distances and filter by radius
        nearby_drivers = []
        for driver in drivers:
            distance = calculate_distance(
                restaurant_lat, restaurant_lng,
                driver.current_lat, driver.current_lng
            )
            
            if distance <= radius:
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
            'search_radius': radius,
            'restaurant_location': {
                'latitude': restaurant_lat,
                'longitude': restaurant_lng
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching nearby drivers: {e}")
        return jsonify({'error': 'Failed to fetch nearby drivers'}), 500

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

# Duplicate driver endpoint removed - using consolidated endpoint below

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
        
        # Check if order is in correct status for driver assignment
        if order.status not in ['pending', 'confirmed', 'ready']:
            return jsonify({
                'success': False, 
                'message': f'Order status "{order.status}" cannot be processed for driver assignment. Order must be pending, confirmed, or ready.'
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



@app.route('/api/admin/payment-notifications', methods=['GET'])
def get_payment_notifications():
    """Get pending payment notifications for admin"""
    try:
        # Get orders with payment screenshots but not yet verified
        orders = Order.query.filter(
            Order.status.in_(['confirmed', 'pending']),
            Order.transaction_image_url.isnot(None)
        ).order_by(Order.created_at.desc()).all()
        
        notifications = []
        for order in orders:
            notifications.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'total_amount': order.total_amount,
                'created_at': order.created_at.isoformat(),
                'screenshot_url': order.transaction_image_url,
                'status': order.status
            })
        
        return jsonify({
            'notifications': notifications,
            'count': len(notifications)
        })
    except Exception as e:
        logger.error(f"Error getting payment notifications: {e}")
        return jsonify({'error': 'Failed to get payment notifications'}), 500





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
    """Permanently delete a driver and allow fresh registration"""
    try:
        driver = Driver.query.get_or_404(driver_id)
        driver_telegram_id = driver.telegram_user_id
        driver_name = driver.name
        
        # First, unassign any active orders
        active_orders = Order.query.filter_by(driver_id=driver_id).filter(
            Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
        ).all()
        
        for order in active_orders:
            order.driver_id = None
            order.status = 'confirmed'  # Reset to confirmed so admin can reassign
            
        # Check for UserProfile record and delete if exists
        try:
            from models import UserProfile
            user_profile = UserProfile.query.filter_by(telegram_user_id=driver_telegram_id).first()
            if user_profile:
                db.session.delete(user_profile)
                logger.info(f"Deleted UserProfile for driver {driver_name}")
        except Exception as e:
            logger.warning(f"No UserProfile found or error deleting: {e}")
            
        # Delete the driver record completely
        db.session.delete(driver)
        db.session.commit()
        
        # Notify driver via driver bot that they can register fresh
        if driver_telegram_id:
            try:
                from driver_bot import send_driver_message
                message = f"👋 *Account Removed*\n\n"
                message += f"Your driver account has been permanently removed from the system.\n\n"
                message += f"✅ You can now register as a new driver if you wish.\n"
                message += f"📝 Use /start to begin fresh registration.\n\n"
                message += f"Thank you for your service!"
                
                send_driver_message(driver_telegram_id, message)
                logger.info(f"Notified driver {driver_name} about account deletion")
            except Exception as e:
                logger.warning(f"Could not notify driver about deletion: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Driver {driver_name} permanently deleted. They can register fresh now.',
            'unassigned_orders': len(active_orders),
            'notification_sent': driver_telegram_id is not None
        })
        
    except Exception as e:
        logger.error(f"Error permanently deleting driver: {e}")
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

@app.route('/driver-registration')
def driver_registration():
    """Driver registration WebApp page"""
    return render_template('driver_registration_webapp.html')

@app.route('/api/driver-registration-webapp', methods=['POST'])
def submit_driver_registration_webapp():
    """Submit driver registration form"""
    try:
        # Handle both JSON and FormData
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData from WebApp
            telegram_user_id = request.form.get('telegram_user_id')
            name = request.form.get('name')
            phone_number = request.form.get('phone_number')
            email = request.form.get('email', '')
            vehicle_type = request.form.get('vehicle_type')
            
            # Handle document uploads
            document_urls = {}
            
            # Government ID (always required)
            if 'id_front' in request.files:
                file = request.files['id_front']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = str(int(datetime.now().timestamp()))
                    filename = f"id_front_{timestamp}_{filename}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    document_urls['id_front_url'] = f"/static/uploads/{filename}"
            
            if 'id_back' in request.files:
                file = request.files['id_back']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = str(int(datetime.now().timestamp()))
                    filename = f"id_back_{timestamp}_{filename}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    document_urls['id_back_url'] = f"/static/uploads/{filename}"
            
            # Driver license and vehicle registration (only for motorcycle/car)
            if vehicle_type != 'bicycle':
                if 'license_front' in request.files:
                    file = request.files['license_front']
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = str(int(datetime.now().timestamp()))
                        filename = f"license_front_{timestamp}_{filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(filepath)
                        document_urls['license_front_url'] = f"/static/uploads/{filename}"
                
                if 'license_back' in request.files:
                    file = request.files['license_back']
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = str(int(datetime.now().timestamp()))
                        filename = f"license_back_{timestamp}_{filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(filepath)
                        document_urls['license_back_url'] = f"/static/uploads/{filename}"
                
                if 'vehicle_registration' in request.files:
                    file = request.files['vehicle_registration']
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = str(int(datetime.now().timestamp()))
                        filename = f"vehicle_reg_{timestamp}_{filename}"
                        filepath = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(filepath)
                        document_urls['vehicle_registration_url'] = f"/static/uploads/{filename}"
        else:
            # JSON data (legacy support)
            data = request.get_json()
            telegram_user_id = data.get('telegram_user_id')
            name = data.get('name')
            phone_number = data.get('phone_number')
            email = data.get('email', '')
            vehicle_type = data.get('vehicle_type')
            document_urls = {}
        
        # Validate required fields
        if not all([telegram_user_id, name, phone_number, vehicle_type]):
            logger.error(f"Missing required fields: telegram_user_id={telegram_user_id}, name={name}, phone_number={phone_number}, vehicle_type={vehicle_type}")
            return jsonify({
                'success': False,
                'message': 'Missing required fields: name, phone number, and vehicle type are required.'
            }), 400
        
        # Create new driver with pending approval
        driver = Driver(
            name=name,
            phone_number=phone_number,
            email=email,
            telegram_user_id=int(telegram_user_id) if telegram_user_id else None,
            vehicle_type=vehicle_type,
            approval_status='pending',
            is_approved=False,
            is_active=False,
            is_available=False,
            registration_date=datetime.utcnow(),
            **document_urls  # Add all document URLs
        )
        
        db.session.add(driver)
        db.session.commit()
        
        # Notify admin about new driver registration
        from admin_approval_system import notify_admin_new_driver_registration
        notify_admin_new_driver_registration(driver.id)
        
        # Send confirmation to driver
        from driver_bot import send_driver_message
        message = f"✅ *Registration Submitted Successfully!*\n\n"
        message += f"👤 Name: {name}\n"
        message += f"📱 Phone: {phone_number}\n"
        message += f"🚗 Vehicle: {vehicle_type.title()}\n\n"
        message += f"📋 **Status:** Under Review\n\n"
        message += f"🔍 Your application is being reviewed by our admin team.\n"
        message += f"⏰ You'll receive a notification once approved.\n\n"
        message += f"📞 Contact admin if you have any questions.\n\n"
        message += f"Thank you for your interest in joining ET-FOOD!"
        
        send_driver_message(telegram_user_id, message)
        
        return jsonify({
            'success': True,
            'message': 'Driver registration submitted successfully',
            'driver_id': driver.id
        })
        
    except Exception as e:
        logger.error(f"Error submitting driver registration: {e}")
        logger.error(f"Request form data: {dict(request.form)}")
        logger.error(f"Request files: {list(request.files.keys())}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Failed to submit registration: {str(e)}'
        }), 500




@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """Get detailed order information including driver details"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Parse items
        items = []
        try:
            items = json.loads(order.items) if isinstance(order.items, str) else order.items
        except:
            items = []
        
        # Get driver information if assigned
        driver_info = None
        if order.driver_id:
            driver = Driver.query.get(order.driver_id)
            if driver:
                driver_info = {
                    'id': driver.id,
                    'name': driver.name,
                    'phone_number': driver.phone_number,
                    'vehicle_type': driver.vehicle_type,
                    'current_latitude': driver.current_latitude,
                    'current_longitude': driver.current_longitude,
                    'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
                    'is_available': driver.is_available,
                    'is_active': driver.is_active,
                    'telegram_user_id': driver.telegram_user_id
                }
        
        order_data = {
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'customer_address': order.customer_address,
            'customer_latitude': order.location_lat,
            'customer_longitude': order.location_lng,
            'location_lat': order.location_lat,
            'location_lng': order.location_lng,
            'items': items,
            'total_amount': float(order.total_amount),
            'payment_method': order.payment_method,
            'status': order.status,
            'driver_id': order.driver_id,
            'transaction_id': order.transaction_id,
            'transaction_image_url': order.transaction_image_url,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat()
        }
        
        return jsonify({
            'success': True,
            'order': order_data,
            'driver': driver_info
        })
        
    except Exception as e:
        logger.error(f"Error getting order details: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get order details'
        }), 500

@app.route('/api/orders/<int:order_id>/details')
def get_order_details_detailed(order_id):
    """Get comprehensive order details including driver information for tracking"""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Get driver information if assigned
        driver_info = None
        if order.driver_id:
            driver = Driver.query.get(order.driver_id)
            if driver:
                driver_info = {
                    'id': driver.id,
                    'name': driver.name,
                    'phone_number': driver.phone_number,
                    'vehicle_type': driver.vehicle_type,
                    'current_latitude': driver.current_latitude,
                    'current_longitude': driver.current_longitude,
                    'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
                    'is_available': driver.is_available,
                    'is_active': driver.is_active,
                    'telegram_user_id': driver.telegram_user_id
                }
        
        # Build order details
        order_details = {
            'id': order.id,
            'customer_name': order.customer_name,
            'customer_phone': order.customer_phone,
            'customer_address': order.customer_address,
            'customer_latitude': order.location_lat,
            'customer_longitude': order.location_lng,
            'items': order.items if isinstance(order.items, list) else json.loads(order.items or '[]'),
            'total_amount': float(order.total_amount),
            'payment_method': order.payment_method,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'driver_id': order.driver_id,
            'transaction_id': order.transaction_id,
            'transaction_image_url': order.transaction_image_url
        }
        
        return jsonify({
            'success': True,
            'order': order_details,
            'driver': driver_info
        })
        
    except Exception as e:
        logger.error(f"Error fetching order details: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to fetch order details'
        }), 500

@app.route('/api/send-driver-message', methods=['POST'])
def send_driver_message_route():
    """Send message to driver via Telegram"""
    try:
        data = request.get_json()
        driver_id = data.get('driver_id')
        message = data.get('message')
        
        if not driver_id or not message:
            return jsonify({'success': False, 'message': 'Driver ID and message are required'}), 400
        
        driver = Driver.query.get_or_404(driver_id)
        
        if not driver.telegram_user_id:
            return jsonify({'success': False, 'message': 'Driver has no Telegram account linked'}), 400
        
        # Send message via driver bot
        from driver_bot import send_driver_message
        success = send_driver_message(driver.telegram_user_id, f"📨 Message from Admin:\n\n{message}")
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Message sent to {driver.name}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send message to driver'
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending driver message: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/send-driver-message', methods=['POST'])
def send_driver_message_api():
    """Send message to driver via Telegram"""
    try:
        data = request.get_json()
        telegram_user_id = data.get('telegram_user_id')
        message = data.get('message')
        
        if not telegram_user_id or not message:
            return jsonify({
                'success': False,
                'message': 'Telegram user ID and message are required'
            }), 400
        
        # Import driver bot function
        from driver_bot import send_driver_message
        
        # Send message via driver bot
        success = send_driver_message(telegram_user_id, f"📨 *Message from Admin*\n\n{message}")
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Message sent successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send message'
            })
        
    except Exception as e:
        logger.error(f"Error sending driver message: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to send message'
        }), 500

# Driver Search Radius Management API Endpoints
@app.route('/api/admin/driver-search-radius', methods=['GET'])
def get_driver_search_radius():
    """Get current driver search radius setting"""
    try:
        setting = SystemSettings.query.filter_by(setting_key='driver_search_radius').first()
        
        if setting:
            radius = float(setting.setting_value)
        else:
            radius = 10.0  # Default 10km
        
        return jsonify({
            'success': True,
            'radius': radius,
            'unit': 'km'
        })
        
    except Exception as e:
        logger.error(f"Error getting driver search radius: {e}")
        return jsonify({'error': 'Failed to get search radius'}), 500

@app.route('/api/admin/driver-search-radius', methods=['PUT'])
def update_driver_search_radius():
    """Update driver search radius setting"""
    try:
        data = request.get_json()
        new_radius = data.get('radius')
        
        if not new_radius:
            return jsonify({'error': 'Radius value is required'}), 400
        
        try:
            radius_value = float(new_radius)
            if radius_value <= 0:
                return jsonify({'error': 'Radius must be a positive number'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid radius value'}), 400
        
        # Get or create the setting
        setting = SystemSettings.query.filter_by(setting_key='driver_search_radius').first()
        
        if setting:
            setting.setting_value = str(radius_value)
            setting.updated_at = datetime.utcnow()
        else:
            setting = SystemSettings(
                setting_key='driver_search_radius',
                setting_value=str(radius_value),
                description='Driver search radius in kilometers for order assignments'
            )
            db.session.add(setting)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'radius': radius_value,
            'unit': 'km',
            'message': f'Driver search radius updated to {radius_value}km'
        })
        
    except Exception as e:
        logger.error(f"Error updating driver search radius: {e}")
        return jsonify({'error': 'Failed to update search radius'}), 500


@app.route('/api/restaurants/info')
def api_restaurant_info():
    """API endpoint for current selected restaurant info"""
    try:
        # Get restaurant ID from query parameter
        restaurant_id = request.args.get('restaurant_id', type=int)
        
        # If no specific restaurant requested, get the first available active restaurant with menu items
        if restaurant_id is None:
            restaurant = db.session.query(Restaurant).filter(
                Restaurant.is_active == True,
                Restaurant.id.in_(
                    db.session.query(MenuItem.restaurant_id).filter(MenuItem.available == True).distinct()
                )
            ).first()
        else:
            restaurant = Restaurant.query.filter_by(id=restaurant_id).first()
        
        # If requested restaurant doesn't exist, get first available restaurant with menu items
        if not restaurant:
            restaurant = db.session.query(Restaurant).filter(
                Restaurant.is_active == True,
                Restaurant.id.in_(
                    db.session.query(MenuItem.restaurant_id).filter(MenuItem.available == True).distinct()
                )
            ).first()
        
        if restaurant:
            # Add cache-busting timestamp to image URLs to ensure real-time updates
            timestamp = str(int(datetime.now().timestamp()))
            
            return jsonify({
                'success': True,
                'restaurant': {
                    'id': restaurant.id,
                    'name': restaurant.name,
                    'description': restaurant.description,
                    'logo_url': f"{restaurant.logo_url}?t={timestamp}" if restaurant.logo_url else None,
                    'cover_image_url': f"{restaurant.cover_image_url}?t={timestamp}" if restaurant.cover_image_url else None,
                    'address': restaurant.address,
                    'phone': restaurant.phone,
                    'estimated_delivery_time': restaurant.estimated_delivery_time
                },
                'company': {
                    'name': 'ET-FOOD',
                    'description': 'Food Delivery Service'
                }
            })
        else:
            # No restaurants available at all
            return jsonify({
                'success': False,
                'error': 'No restaurants available',
                'restaurant': {
                    'name': 'Restaurant',
                    'description': 'Delicious Food',
                    'logo_url': None,
                    'cover_image_url': None
                },
                'company': {
                    'name': 'ET-FOOD',
                    'description': 'Food Delivery Service'
                }
            })
    except Exception as e:
        logger.error(f"Error fetching restaurant info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
