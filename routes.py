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

logger = logging.getLogger(__name__)

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        
        # Notify driver about assignment
        from bot_minimal import notify_driver_assignment
        notify_driver_assignment(driver_id, order_id)
        
        return jsonify({'success': True, 'message': f'Driver {driver.name} assigned to order #{order_id}'})
    except Exception as e:
        logger.error(f"Error assigning driver: {e}")
        return jsonify({'error': 'Failed to assign driver'}), 500

