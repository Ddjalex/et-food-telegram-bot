from flask import request, jsonify, render_template, session, redirect, url_for, flash
from app import app, db
from models import MenuItem, Category, Restaurant, Order, AdminUser, AdminSession, AdminActivity
from datetime import datetime
import logging
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from functools import wraps

logger = logging.getLogger(__name__)

def kitchen_staff_required(f):
    """Decorator to require kitchen staff or admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('kitchen_login'))
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or not admin.is_active:
            session.clear()
            return redirect(url_for('kitchen_login'))
        
        # Allow kitchen staff and admins to access kitchen dashboard
        if admin.role not in ['kitchen_staff', 'admin', 'super_admin']:
            return redirect(url_for('kitchen_login'))
        
        return f(*args, **kwargs)
    return decorated_function

# Kitchen login route
@app.route('/kitchen/login', methods=['GET', 'POST'])
def kitchen_login():
    """Kitchen staff login page"""
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
            
            # Check if user has kitchen access
            if admin.role not in ['kitchen_staff', 'admin', 'super_admin']:
                return jsonify({'success': False, 'message': 'No kitchen access permissions'}), 403
            
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
                return jsonify({'success': True, 'role': admin.role, 'redirect': '/kitchen'})
            else:
                return redirect('/kitchen')
        
        # Handle error response
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        else:
            return render_template('kitchen_login.html', error='Invalid credentials')
    
    return render_template('kitchen_login.html')

# Kitchen staff access routes
@app.route('/kitchen')
@kitchen_staff_required
def kitchen_dashboard():
    """Kitchen staff dashboard - requires authentication"""
    admin = AdminUser.query.get(session['admin_id'])
    return render_template('kitchen_dashboard.html', admin=admin)

@app.route('/kitchen/menu')
@kitchen_staff_required
def kitchen_menu_management():
    """Kitchen staff menu management page"""
    return render_template('kitchen_menu_management.html')

@app.route('/kitchen/orders', methods=['GET'])
@kitchen_staff_required
def kitchen_get_orders():
    """Get orders for kitchen staff"""
    try:
        restaurant_id = request.args.get('restaurant_id', 1)
        
        orders = Order.query.filter_by(restaurant_id=restaurant_id).filter(
            Order.status.in_(['pending', 'confirmed', 'preparing', 'ready'])
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            # Calculate minutes ago
            minutes_ago = int((datetime.utcnow() - order.created_at).total_seconds() / 60)
            
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
                'payment_method': order.payment_method,
                'created_at': order.created_at.isoformat(),
                'minutes_ago': minutes_ago,
                'items': items
            })
        
        return jsonify(orders_data)
    except Exception as e:
        logger.error(f"Error getting kitchen orders: {e}")
        return jsonify({'error': str(e)}), 500

# Kitchen API endpoints for menu management
@app.route('/api/kitchen/menu-items', methods=['GET'])
@kitchen_staff_required
def kitchen_get_menu_items():
    """Get all menu items for kitchen staff"""
    try:
        restaurant_id = request.args.get('restaurant_id', 1)
        menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
        return jsonify({
            'success': True,
            'menu_items': [item.to_dict() for item in menu_items]
        })
    except Exception as e:
        logger.error(f"Error fetching menu items for kitchen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/menu-items', methods=['POST'])
@kitchen_staff_required
def kitchen_create_menu_item():
    """Create new menu item (kitchen staff)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'price', 'category_id', 'restaurant_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Create new menu item
        menu_item = MenuItem(
            name=data['name'],
            description=data.get('description', ''),
            price=float(data['price']),
            category_id=int(data['category_id']),
            restaurant_id=int(data['restaurant_id']),
            image_url=data.get('image_url', ''),
            available=data.get('available', True)
        )
        
        db.session.add(menu_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Menu item created successfully',
            'menu_item': menu_item.to_dict()
        })
    except Exception as e:
        logger.error(f"Error creating menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/menu-items/<int:item_id>', methods=['PUT'])
@kitchen_staff_required
def kitchen_update_menu_item(item_id):
    """Update menu item (kitchen staff)"""
    try:
        menu_item = MenuItem.query.get_or_404(item_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            menu_item.name = data['name']
        if 'description' in data:
            menu_item.description = data['description']
        if 'price' in data:
            menu_item.price = float(data['price'])
        if 'category_id' in data:
            menu_item.category_id = int(data['category_id'])
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
        logger.error(f"Error updating menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/menu-items/<int:item_id>', methods=['DELETE'])
@kitchen_staff_required
def kitchen_delete_menu_item(item_id):
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
        logger.error(f"Error deleting menu item: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories', methods=['GET'])
@kitchen_staff_required
def kitchen_get_categories():
    """Get all categories for kitchen staff"""
    try:
        categories = Category.query.all()
        return jsonify({
            'success': True,
            'categories': [category.to_dict() for category in categories]
        })
    except Exception as e:
        logger.error(f"Error fetching categories for kitchen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories', methods=['POST'])
@kitchen_staff_required
def kitchen_create_category():
    """Create new category (kitchen staff)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Category name is required'}), 400
        
        # Create new category
        category = Category(
            name=data['name'],
            description=data.get('description', ''),
            icon=data.get('icon', '🍽️'),
            image_url=data.get('image_url', ''),
            sort_order=data.get('sort_order', 0)
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category created successfully',
            'category': category.to_dict()
        })
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories/<int:category_id>', methods=['PUT'])
@kitchen_staff_required
def kitchen_update_category(category_id):
    """Update category (kitchen staff)"""
    try:
        category = Category.query.get_or_404(category_id)
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        if 'icon' in data:
            category.icon = data['icon']
        if 'image_url' in data:
            category.image_url = data['image_url']
        if 'sort_order' in data:
            category.sort_order = int(data['sort_order'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category updated successfully',
            'category': category.to_dict()
        })
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/categories/<int:category_id>', methods=['DELETE'])
@kitchen_staff_required
def kitchen_delete_category(category_id):
    """Delete category (kitchen staff)"""
    try:
        category = Category.query.get_or_404(category_id)
        
        # Check if category has menu items
        menu_items_count = MenuItem.query.filter_by(category_id=category_id).count()
        if menu_items_count > 0:
            return jsonify({
                'success': False, 
                'error': f'Cannot delete category with {menu_items_count} menu items. Move or delete items first.'
            }), 400
        
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/upload-image', methods=['POST'])
@kitchen_staff_required
def kitchen_upload_image():
    """Upload image for menu items or categories"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Invalid file type. Only PNG, JPG, JPEG, GIF, and WebP are allowed.'}), 400
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.static_folder, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Return URL for the uploaded image
        image_url = f"/static/uploads/{filename}"
        
        return jsonify({
            'success': True,
            'image_url': image_url,
            'filename': filename
        })
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/restaurants', methods=['GET'])
@kitchen_staff_required
def kitchen_get_restaurants():
    """Get all restaurants for kitchen staff"""
    try:
        restaurants = Restaurant.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'restaurants': [restaurant.to_dict() for restaurant in restaurants]
        })
    except Exception as e:
        logger.error(f"Error fetching restaurants for kitchen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Kitchen API Routes
@app.route('/api/kitchen/orders')
@kitchen_staff_required 
def kitchen_get_orders():
    """Get orders for kitchen staff - filtered by restaurant"""
    try:
        # Get the current kitchen staff's restaurant
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or not admin.restaurant_id:
            return jsonify({'success': False, 'error': 'Kitchen staff not associated with a restaurant'}), 403
        
        import json
        orders = Order.query.filter(
            Order.restaurant_id == admin.restaurant_id,  # CRITICAL FIX: Filter by restaurant
            Order.status.in_(['pending', 'confirmed', 'preparing', 'ready'])
        ).order_by(Order.created_at.desc()).all()
        
        orders_data = []
        for order in orders:
            # Parse items properly
            items = []
            if order.items:
                try:
                    if isinstance(order.items, str):
                        items = json.loads(order.items)
                    else:
                        items = order.items
                except:
                    items = []
            
            # Ensure items is a list
            if not isinstance(items, list):
                items = []
            
            # Add image URL for each item
            for item in items:
                if isinstance(item, dict):
                    # Try to find the menu item to get the image
                    menu_item = MenuItem.query.filter_by(name=item.get('name')).first()
                    if menu_item and menu_item.image_url:
                        item['image'] = menu_item.image_url
                    else:
                        item['image'] = '/static/placeholder-food.jpg'
                    
                    # Ensure all required fields are present
                    item['name'] = item.get('name', 'Unknown Item')
                    item['price'] = item.get('price', 0)
                    item['quantity'] = item.get('quantity', 1)
            
            order_dict = {
                'id': order.id,
                'customer_name': order.customer_name or 'Unknown Customer',
                'phone': order.phone or 'No phone',
                'address': order.address or 'Pickup at restaurant',
                'items': items,
                'total': float(order.total) if order.total else 0,
                'status': order.status,
                'payment_method': order.payment_method,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'special_instructions': order.special_instructions
            }
            orders_data.append(order_dict)
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'total_orders': len(orders_data)
        })
    except Exception as e:
        logger.error(f"Error fetching kitchen orders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/kitchen/orders/<int:order_id>/status', methods=['PUT', 'POST'])
@kitchen_staff_required
def kitchen_update_order_status_api(order_id):
    """Update order status from kitchen"""
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['confirmed', 'preparing', 'ready', 'cancelled']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400
        
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log the status change
        logger.info(f"Kitchen updated order #{order_id} status from {old_status} to {new_status}")
        
        # Notify customer about status change
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, new_status)
        except Exception as e:
            logger.error(f"Error notifying customer about status change: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {new_status}'
        })
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/kitchen/confirm-availability/<int:order_id>', methods=['POST'])
@kitchen_staff_required
def kitchen_confirm_availability(order_id):
    """Kitchen staff confirms or rejects order availability"""
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        available = data.get('available', True)
        reason = data.get('reason', '')
        
        logger.info(f"Kitchen confirming availability for order #{order_id}: available={available}")
        
        if available:
            # Kitchen accepts the order - trigger customer payment request
            order.status = 'kitchen_accepted'
            order.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Import and call the enhanced kitchen workflow
            try:
                from enhanced_kitchen_workflow import handle_kitchen_acceptance
                handle_kitchen_acceptance(order_id)
                logger.info(f"Successfully triggered customer payment request for order #{order_id}")
            except Exception as e:
                logger.error(f"Error in enhanced kitchen workflow: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Order accepted! Customer has been notified to make payment.'
            })
        else:
            # Kitchen rejects the order
            order.status = 'cancelled'
            order.cancellation_reason = reason
            order.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Notify customer about rejection
            try:
                from bot_minimal import notify_customer_order_rejected
                notify_customer_order_rejected(order_id, reason)
                logger.info(f"Customer notified about order #{order_id} rejection")
            except Exception as e:
                logger.error(f"Error notifying customer about rejection: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Order marked as unavailable. Customer has been notified. Reason: {reason}'
            })
            
    except Exception as e:
        logger.error(f"Error confirming availability for order {order_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Alternative endpoint to match JavaScript calls from kitchen dashboard
@app.route('/api/orders/<int:order_id>/status', methods=['POST'])
@kitchen_staff_required
def kitchen_update_order_status_alternative(order_id):
    """Alternative endpoint for order status updates from kitchen dashboard"""
    return kitchen_update_order_status_api(order_id)

@app.route('/api/kitchen/analytics')
@kitchen_staff_required
def kitchen_get_analytics_api():
    """Get kitchen analytics data"""
    try:
        from datetime import timedelta
        from sqlalchemy import func
        import json
        
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        # Today's orders
        today_orders = Order.query.filter(
            func.date(Order.created_at) == today
        ).count()
        
        # This week's orders
        week_orders = Order.query.filter(
            Order.created_at >= week_ago
        ).count()
        
        # Orders by status
        status_counts = {}
        statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled']
        for status in statuses:
            count = Order.query.filter_by(status=status).count()
            status_counts[status] = count
        
        # Popular items
        popular_items = []
        try:
            orders_with_items = Order.query.filter(Order.items.isnot(None)).all()
            item_counts = {}
            
            for order in orders_with_items:
                items = []
                if order.items:
                    try:
                        if isinstance(order.items, str):
                            items = json.loads(order.items)
                        else:
                            items = order.items
                    except:
                        items = []
                
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            item_name = item.get('name', 'Unknown')
                            item_counts[item_name] = item_counts.get(item_name, 0) + item.get('quantity', 1)
            
            # Sort by count and get top 5
            sorted_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)
            popular_items = [{'name': name, 'count': count} for name, count in sorted_items[:5]]
        except Exception as e:
            logger.error(f"Error calculating popular items: {e}")
        
        return jsonify({
            'success': True,
            'analytics': {
                'today_orders': today_orders,
                'week_orders': week_orders,
                'status_counts': status_counts,
                'popular_items': popular_items
            }
        })
    except Exception as e:
        logger.error(f"Error fetching kitchen analytics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500