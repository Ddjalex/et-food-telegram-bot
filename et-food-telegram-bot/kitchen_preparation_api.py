"""
Kitchen Preparation API for ET-FOOD
Handles kitchen staff actions and real-time notifications to customers
"""

from flask import Blueprint, request, jsonify, session
from models import db, Order, KitchenStaff, AdminUser
from datetime import datetime
import logging
from functools import wraps

logger = logging.getLogger(__name__)

kitchen_prep = Blueprint('kitchen_prep', __name__)

def kitchen_staff_required(f):
    """Decorator to require kitchen staff authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kitchen_staff_id' not in session:
            logger.warning(f"Kitchen staff authentication failed - no kitchen_staff_id in session")
            return jsonify({'success': False, 'error': 'Kitchen staff authentication required'}), 401
        
        staff = KitchenStaff.query.get(session['kitchen_staff_id'])
        if not staff or not staff.is_active:
            session.clear()
            return jsonify({'success': False, 'error': 'Kitchen staff account not active'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@kitchen_prep.route('/api/kitchen/start-preparing/<int:order_id>', methods=['POST'])
@kitchen_staff_required
def start_preparing_order(order_id):
    """Kitchen staff starts preparing an order - sends real-time notifications"""
    try:
        logger.info(f"Kitchen staff starting preparation for order #{order_id}")
        
        # Get kitchen staff from session
        staff = KitchenStaff.query.get(session['kitchen_staff_id'])
        if not staff:
            return jsonify({'success': False, 'error': 'Kitchen staff not found'}), 404
        
        # Find order belonging to same restaurant as kitchen staff
        order = Order.query.filter_by(
            id=order_id, 
            restaurant_id=staff.restaurant_id
        ).first()
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found or access denied'}), 404
        
        # Check if order is ready for preparation (payment must be verified)
        if order.status != 'confirmed' or not order.payment_verified_at:
            return jsonify({
                'success': False, 
                'error': 'Order payment must be verified before preparation can start'
            }), 400
        
        # Check if already being prepared
        if order.status == 'preparing':
            return jsonify({
                'success': False, 
                'error': 'Order is already being prepared'
            }), 400
        
        # Update order status to preparing
        old_status = order.status
        order.status = 'preparing'
        order.preparation_started_at = datetime.utcnow()
        order.assigned_kitchen_staff_id = staff.id
        order.preparation_notes = f"Started by {staff.name} at {datetime.utcnow().strftime('%H:%M')}"
        
        db.session.commit()
        
        # Send real-time notifications
        notifications_sent = []
        
        # 1. Notify customer that preparation started
        try:
            from real_time_notifications import notify_customer_order_preparing
            customer_notified = notify_customer_order_preparing(order, staff.name)
            if customer_notified:
                notifications_sent.append('Customer')
                logger.info(f"Customer notified that preparation started for order #{order_id}")
        except Exception as e:
            logger.error(f"Error notifying customer about preparation start: {e}")
        
        # 2. Notify admin about kitchen activity
        try:
            from real_time_notifications import notify_admin_kitchen_started
            admin_notifications = notify_admin_kitchen_started(order, staff.name)
            if admin_notifications:
                notifications_sent.extend(admin_notifications)
                logger.info(f"Admin notified about preparation start for order #{order_id}")
        except Exception as e:
            logger.error(f"Error notifying admin about preparation start: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Order #{order_id} preparation started by {staff.name}',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': 'preparing',
            'kitchen_staff': staff.name,
            'started_at': order.preparation_started_at.isoformat(),
            'notifications_sent': notifications_sent
        })
        
    except Exception as e:
        logger.error(f"Error starting preparation for order #{order_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@kitchen_prep.route('/api/kitchen/orders/pending', methods=['GET'])
@kitchen_staff_required
def get_pending_orders():
    """Get orders that are ready for preparation by kitchen staff"""
    try:
        # Get kitchen staff from session
        staff = KitchenStaff.query.get(session['kitchen_staff_id'])
        if not staff:
            return jsonify({'success': False, 'error': 'Kitchen staff not found'}), 404
        
        # Get confirmed orders that haven't started preparation yet
        pending_orders = Order.query.filter(
            Order.restaurant_id == staff.restaurant_id,
            Order.status == 'confirmed',
            Order.payment_verified_at.isnot(None)
        ).order_by(Order.created_at.asc()).all()
        
        orders_data = []
        for order in pending_orders:
            order_data = {
                'id': order.id,
                'customer_name': order.customer_name or 'N/A',
                'customer_phone': order.customer_phone or 'N/A',
                'total_amount': float(order.total_amount or 0),
                'items': order.items or 'N/A',
                'delivery_address': order.delivery_address or order.customer_address or 'N/A',
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'payment_verified_at': order.payment_verified_at.isoformat() if order.payment_verified_at else None,
                'waiting_time': _calculate_waiting_time(order.payment_verified_at) if order.payment_verified_at else 'Unknown'
            }
            orders_data.append(order_data)
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'count': len(orders_data),
            'kitchen_staff': staff.name
        })
        
    except Exception as e:
        logger.error(f"Error getting pending orders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@kitchen_prep.route('/api/kitchen/orders/in-progress', methods=['GET'])
@kitchen_staff_required  
def get_in_progress_orders():
    """Get orders currently being prepared"""
    try:
        # Get kitchen staff from session
        staff = KitchenStaff.query.get(session['kitchen_staff_id'])
        if not staff:
            return jsonify({'success': False, 'error': 'Kitchen staff not found'}), 404
        
        # Get orders currently being prepared
        in_progress_orders = Order.query.filter(
            Order.restaurant_id == staff.restaurant_id,
            Order.status == 'preparing'
        ).order_by(Order.preparation_started_at.asc()).all()
        
        orders_data = []
        for order in in_progress_orders:
            # Get assigned kitchen staff name
            assigned_staff = KitchenStaff.query.get(order.assigned_kitchen_staff_id) if order.assigned_kitchen_staff_id else None
            
            order_data = {
                'id': order.id,
                'customer_name': order.customer_name or 'N/A',
                'customer_phone': order.customer_phone or 'N/A', 
                'total_amount': float(order.total_amount or 0),
                'items': order.items or 'N/A',
                'delivery_address': order.delivery_address or order.customer_address or 'N/A',
                'preparation_started_at': order.preparation_started_at.isoformat() if order.preparation_started_at else None,
                'assigned_to': assigned_staff.name if assigned_staff else 'Unknown',
                'preparation_time': _calculate_preparation_time(order.preparation_started_at) if order.preparation_started_at else 'Unknown'
            }
            orders_data.append(order_data)
        
        return jsonify({
            'success': True,
            'orders': orders_data,
            'count': len(orders_data),
            'kitchen_staff': staff.name
        })
        
    except Exception as e:
        logger.error(f"Error getting in-progress orders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def _calculate_waiting_time(payment_verified_at):
    """Calculate how long order has been waiting for preparation"""
    if not payment_verified_at:
        return 'Unknown'
    
    now = datetime.utcnow()
    diff = now - payment_verified_at
    
    if diff.total_seconds() < 60:
        return 'Just now'
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f'{minutes} min ago'
    else:
        hours = int(diff.total_seconds() / 3600)
        minutes = int((diff.total_seconds() % 3600) / 60)
        return f'{hours}h {minutes}m ago'

def _calculate_preparation_time(preparation_started_at):
    """Calculate how long order has been in preparation"""
    if not preparation_started_at:
        return 'Unknown'
    
    now = datetime.utcnow()
    diff = now - preparation_started_at
    
    if diff.total_seconds() < 60:
        return 'Just started'
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f'{minutes} min'
    else:
        hours = int(diff.total_seconds() / 3600)
        minutes = int((diff.total_seconds() % 3600) / 60)
        return f'{hours}h {minutes}m'