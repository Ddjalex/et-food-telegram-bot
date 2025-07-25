"""
Enhanced Payment Verification System for ET-FOOD
Provides real-time, responsive payment verification for restaurant admins
"""

from flask import Blueprint, request, jsonify, session
from models import db, Order, AdminUser, KitchenStaff, Restaurant
from datetime import datetime
import logging
from functools import wraps

logger = logging.getLogger(__name__)

enhanced_payment = Blueprint('enhanced_payment', __name__)

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            logger.warning(f"Admin authentication failed - no admin_id in session. Session keys: {list(session.keys())}")
            if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin or not admin.is_active:
            session.clear()
            if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Account not active'}), 401
            return jsonify({'success': False, 'error': 'Account not active'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@enhanced_payment.route('/api/admin/payment-verification-enhanced', methods=['GET'])
@admin_required
def get_enhanced_payment_verification():
    """Enhanced payment verification endpoint with real-time data"""
    try:
        logger.info(f"Enhanced payment verification accessed. Session: {dict(session)}")
        
        # Check authentication
        if 'admin_id' not in session:
            logger.warning("Admin not authenticated - no admin_id in session")
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            logger.warning(f"Admin not found for ID: {session['admin_id']}")
            return jsonify({'success': False, 'error': 'Admin not found'}), 404
        
        logger.info(f"Enhanced payment verification for admin: {admin.username} (Restaurant: {admin.restaurant_id})")
        
        # Get restaurant-specific orders needing verification
        restaurant_id = admin.restaurant_id or 1
        
        # Enhanced query to get all orders needing verification
        orders = Order.query.filter(
            Order.restaurant_id == restaurant_id,
            Order.status.in_(['pending', 'confirmed']),
            db.or_(
                Order.payment_verified_at.is_(None),
                Order.transaction_image_url.isnot(None)
            )
        ).order_by(Order.created_at.desc()).all()
        
        # Format orders with enhanced data
        verification_orders = []
        for order in orders:
            order_data = {
                'id': order.id,
                'customer_name': order.customer_name or 'N/A',
                'customer_phone': getattr(order, 'customer_phone', 'N/A'),
                'total_amount': float(order.total_amount or 0),
                'payment_method': order.payment_method or 'Manual Verification Required',
                'transaction_id': order.transaction_id or 'N/A',
                'transaction_image_url': order.transaction_image_url,
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'payment_verified_at': order.payment_verified_at.isoformat() if order.payment_verified_at else None,
                'items_count': len(order.items.split(',')) if order.items else 0,
                'delivery_address': order.delivery_address or 'N/A',
                'needs_verification': order.payment_verified_at is None,
                'has_screenshot': order.transaction_image_url is not None,
                'time_since_order': _calculate_time_since(order.created_at) if order.created_at else 'Unknown'
            }
            verification_orders.append(order_data)
        
        # Calculate statistics
        total_pending = len([o for o in verification_orders if o['needs_verification']])
        with_screenshots = len([o for o in verification_orders if o['has_screenshot']])
        manual_verification = len([o for o in verification_orders if not o['has_screenshot']])
        
        logger.info(f"Found {len(verification_orders)} orders for verification (pending: {total_pending})")
        
        return jsonify({
            'success': True,
            'orders': verification_orders,
            'statistics': {
                'total_pending': total_pending,
                'with_screenshots': with_screenshots,
                'manual_verification': manual_verification,
                'restaurant_id': restaurant_id,
                'last_updated': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in enhanced payment verification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_payment.route('/api/admin/verify-payment-enhanced/<int:order_id>', methods=['POST'])
@admin_required
def verify_payment_enhanced(order_id):
    """Enhanced payment verification with comprehensive workflow"""
    try:
        # Check authentication
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'success': False, 'error': 'Admin not found'}), 404
        
        # Get verification notes from request
        data = request.get_json() or {}
        verification_notes = data.get('notes', '')
        verification_method = data.get('method', 'manual')
        
        # Find order belonging to admin's restaurant
        restaurant_id = admin.restaurant_id or 1
        order = Order.query.filter_by(id=order_id, restaurant_id=restaurant_id).first()
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found or access denied'}), 404
        
        # Check if already verified
        if order.payment_verified_at:
            return jsonify({'success': False, 'error': 'Payment already verified'}), 400
        
        # Update order with verification
        old_status = order.status
        order.status = 'confirmed'
        order.payment_verified_at = datetime.utcnow()
        order.payment_verification_method = verification_method
        order.payment_verification_notes = verification_notes
        
        # Ensure payment method is set
        if not order.payment_method:
            order.payment_method = 'Manual Verification'
        
        db.session.commit()
        
        # Send notifications
        notifications_sent = []
        
        # 1. Notify kitchen staff
        try:
            kitchen_staff = KitchenStaff.query.filter_by(
                restaurant_id=restaurant_id,
                is_active=True
            ).all()
            
            if kitchen_staff:
                from payment_workflow import notify_kitchen_staff_payment_verified
                notify_kitchen_staff_payment_verified(order)
                notifications_sent.append('kitchen_staff')
        except Exception as e:
            logger.error(f"Error notifying kitchen staff: {e}")
        
        # 2. Notify customer
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, 'confirmed')
            notifications_sent.append('customer')
        except Exception as e:
            logger.error(f"Error notifying customer: {e}")
        
        # 3. Log admin activity
        try:
            from admin_routes import log_admin_activity
            log_admin_activity(
                admin.id,
                'payment_verified',
                'order',
                order_id,
                f'Payment verified for order #{order_id} using {verification_method}' + 
                (f': {verification_notes}' if verification_notes else '')
            )
        except Exception as e:
            logger.error(f"Error logging admin activity: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Payment verified successfully for order #{order_id}',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': 'confirmed',
            'verification_method': verification_method,
            'notifications_sent': notifications_sent,
            'verified_at': order.payment_verified_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in enhanced payment verification: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@enhanced_payment.route('/api/admin/reject-payment-enhanced/<int:order_id>', methods=['POST'])
@admin_required
def reject_payment_enhanced(order_id):
    """Enhanced payment rejection with detailed workflow"""
    try:
        # Check authentication
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        admin = AdminUser.query.get(session['admin_id'])
        if not admin:
            return jsonify({'success': False, 'error': 'Admin not found'}), 404
        
        # Get rejection data from request
        data = request.get_json() or {}
        rejection_reason = data.get('reason', 'Payment rejected by admin')
        rejection_notes = data.get('notes', '')
        
        if not rejection_reason.strip():
            return jsonify({'success': False, 'error': 'Rejection reason is required'}), 400
        
        # Find order belonging to admin's restaurant
        restaurant_id = admin.restaurant_id or 1
        order = Order.query.filter_by(id=order_id, restaurant_id=restaurant_id).first()
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found or access denied'}), 404
        
        # Update order with rejection
        old_status = order.status
        order.status = 'cancelled'
        order.cancellation_reason = rejection_reason
        order.payment_rejected_at = datetime.utcnow()
        order.payment_rejection_notes = rejection_notes
        
        db.session.commit()
        
        # Notify customer about rejection
        try:
            from bot_minimal import notify_customer_status_change
            notify_customer_status_change(order_id, 'cancelled')
        except Exception as e:
            logger.error(f"Error notifying customer about rejection: {e}")
        
        # Log admin activity
        try:
            from admin_routes import log_admin_activity
            log_admin_activity(
                admin.id,
                'payment_rejected',
                'order',
                order_id,
                f'Payment rejected for order #{order_id}: {rejection_reason}' + 
                (f' - {rejection_notes}' if rejection_notes else '')
            )
        except Exception as e:
            logger.error(f"Error logging admin activity: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Payment rejected for order #{order_id}',
            'order_id': order_id,
            'old_status': old_status,
            'new_status': 'cancelled',
            'rejection_reason': rejection_reason,
            'rejected_at': order.payment_rejected_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in enhanced payment rejection: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

def _calculate_time_since(created_at):
    """Calculate human-readable time since order creation"""
    if not created_at:
        return 'Unknown'
    
    try:
        now = datetime.utcnow()
        diff = now - created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    except Exception:
        return 'Unknown'