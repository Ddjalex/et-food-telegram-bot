"""
Kitchen Availability Management Routes
Handles kitchen staff operations for food availability management
"""

from flask import Blueprint, request, jsonify, session
from models import MenuItem, Order, AdminUser, Restaurant, Category
from extensions import db
from food_availability_system import (
    mark_item_unavailable, 
    mark_item_available,
    notify_customer_food_unavailable,
    get_availability_summary,
    bulk_update_availability
)
from bot_minimal import send_message
import json

kitchen_bp = Blueprint('kitchen', __name__)

@kitchen_bp.route('/kitchen-availability')
def kitchen_availability_dashboard():
    """Kitchen availability dashboard page"""
    from flask import render_template
    return render_template('kitchen_availability_dashboard.html')

@kitchen_bp.route('/api/kitchen/menu-items', methods=['GET'])
def get_kitchen_menu_items():
    """Get all menu items for kitchen management"""
    try:
        # Get kitchen staff info from session
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(admin_id)
        if not admin or not admin.restaurant_id:
            return jsonify({'error': 'Admin not found or not associated with restaurant'}), 404
        
        # Get all menu items for this restaurant
        menu_items = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id).all()
        
        items_data = []
        for item in menu_items:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'description': item.description,
                'category': item.category,
                'available': item.available,
                'image_url': item.image_url
            })
        
        return jsonify({
            'items': items_data,
            'total_items': len(items_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kitchen_bp.route('/api/kitchen/toggle-availability', methods=['POST'])
def toggle_item_availability():
    """Toggle availability of a menu item"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        available = data.get('available')
        reason = data.get('reason', 'Kitchen decision')
        
        if not item_id:
            return jsonify({'error': 'Item ID required'}), 400
        
        # Get kitchen staff info from session
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(admin_id)
        if not admin or not admin.restaurant_id:
            return jsonify({'error': 'Admin not found or not associated with restaurant'}), 404
        
        menu_item = MenuItem.query.filter_by(id=item_id, restaurant_id=admin.restaurant_id).first()
        if not menu_item:
            return jsonify({'error': 'Menu item not found'}), 404
        
        if available:
            success = mark_item_available(item_id)
        else:
            success = mark_item_unavailable(item_id, reason)
        
        if success:
            return jsonify({
                'message': f'Item {menu_item.name} marked as {"available" if available else "unavailable"}',
                'item_id': item_id,
                'available': available
            })
        else:
            return jsonify({'error': 'Failed to update availability'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kitchen_bp.route('/api/kitchen/bulk-availability', methods=['POST'])
def bulk_toggle_availability():
    """Bulk toggle availability for multiple items"""
    try:
        data = request.get_json()
        item_ids = data.get('item_ids', [])
        available = data.get('available', True)
        
        if not item_ids:
            return jsonify({'error': 'Item IDs required'}), 400
        
        # Get kitchen staff info from session
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(admin_id)
        if not admin or not admin.restaurant_id:
            return jsonify({'error': 'Admin not found or not associated with restaurant'}), 404
        
        success = bulk_update_availability(admin.restaurant_id, item_ids, available)
        
        if success:
            return jsonify({
                'message': f'{len(item_ids)} items marked as {"available" if available else "unavailable"}',
                'updated_count': len(item_ids)
            })
        else:
            return jsonify({'error': 'Failed to update availability'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kitchen_bp.route('/api/kitchen/availability-summary', methods=['GET'])
def get_kitchen_availability_summary():
    """Get availability summary for kitchen dashboard"""
    try:
        # Get kitchen staff info from session
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(admin_id)
        if not admin or not admin.restaurant_id:
            return jsonify({'error': 'Admin not found or not associated with restaurant'}), 404
        
        summary = get_availability_summary(admin.restaurant_id)
        
        return jsonify(summary)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kitchen_bp.route('/api/kitchen/mark-order-unavailable', methods=['POST'])
def mark_order_unavailable():
    """Mark an order as unavailable and notify customer"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        reason = data.get('reason', 'Items currently unavailable')
        
        if not order_id:
            return jsonify({'error': 'Order ID required'}), 400
        
        # Get kitchen staff info from session
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(admin_id)
        if not admin or not admin.restaurant_id:
            return jsonify({'error': 'Admin not found or not associated with restaurant'}), 404
        
        order = Order.query.filter_by(id=order_id, restaurant_id=admin.restaurant_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Update order status to cancelled
        order.status = 'cancelled'
        db.session.commit()
        
        # Notify customer
        message = f"❌ **Order #{order.id} Cancelled**\n\n"
        message += f"We're sorry to inform you that your order cannot be fulfilled at this time.\n\n"
        message += f"**Reason:** {reason}\n\n"
        message += "Your payment will be refunded within 24 hours.\n\n"
        message += "Thank you for your understanding!"
        
        send_message(order.telegram_user_id, message)
        
        return jsonify({
            'message': 'Order marked as unavailable and customer notified',
            'order_id': order_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kitchen_bp.route('/api/kitchen/categories', methods=['GET'])
def get_kitchen_categories():
    """Get all categories for kitchen management"""
    try:
        # Get kitchen staff info from session
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(admin_id)
        if not admin or not admin.restaurant_id:
            return jsonify({'error': 'Admin not found or not associated with restaurant'}), 404
        
        categories = Category.query.filter_by(restaurant_id=admin.restaurant_id).order_by(Category.sort_order).all()
        
        categories_data = []
        for cat in categories:
            # Count items in this category
            item_count = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id, category=cat.name).count()
            available_count = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id, category=cat.name, available=True).count()
            
            categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'icon': cat.icon,
                'item_count': item_count,
                'available_count': available_count,
                'is_active': cat.is_active
            })
        
        return jsonify({
            'categories': categories_data,
            'total_categories': len(categories_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@kitchen_bp.route('/api/kitchen/category-items/<int:category_id>', methods=['GET'])
def get_category_items(category_id):
    """Get all items in a specific category"""
    try:
        # Get kitchen staff info from session
        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(admin_id)
        if not admin or not admin.restaurant_id:
            return jsonify({'error': 'Admin not found or not associated with restaurant'}), 404
        
        category = Category.query.filter_by(id=category_id, restaurant_id=admin.restaurant_id).first()
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        items = MenuItem.query.filter_by(restaurant_id=admin.restaurant_id, category=category.name).all()
        
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'description': item.description,
                'available': item.available,
                'image_url': item.image_url
            })
        
        return jsonify({
            'category': category.name,
            'items': items_data,
            'total_items': len(items_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Test the routes
    print("Kitchen availability routes created successfully!")