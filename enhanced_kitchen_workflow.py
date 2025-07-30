"""
Enhanced Kitchen Workflow System
Implements real-time order flow: Customer Order → Kitchen Accept → Customer Deposit → Admin Verify → Kitchen Prepare
"""

from flask import Blueprint, request, jsonify
from app import app, db
from models import Order, PaymentTransaction
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

enhanced_kitchen_workflow = Blueprint('enhanced_kitchen_workflow', __name__)

@enhanced_kitchen_workflow.route('/api/kitchen/accept-order', methods=['POST'])
def kitchen_accept_order():
    """Kitchen staff accepts an order and triggers customer deposit notification"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        if order.status != 'pending':
            return jsonify({'error': 'Order is not in pending status'}), 400
        
        # Update order status to accepted
        order.status = 'accepted'
        order.kitchen_accepted_at = datetime.utcnow()
        
        # Calculate deposit amount (50% of total)
        deposit_amount = order.total_amount * 0.5
        order.deposit_amount = deposit_amount
        
        db.session.commit()
        
        # Notify customer to make deposit
        notify_customer_make_deposit(order)
        
        # Log for real-time updates
        logger.info(f"🍽️ KITCHEN ACCEPTED: Order #{order.id} - Deposit required: {deposit_amount:.2f} ETB")
        
        return jsonify({
            'success': True,
            'message': 'Order accepted. Customer notified to make deposit.',
            'order_status': 'accepted',
            'deposit_amount': deposit_amount
        })
        
    except Exception as e:
        logger.error(f"Error accepting order: {e}")
        return jsonify({'error': str(e)}), 500

@enhanced_kitchen_workflow.route('/api/kitchen/reject-order', methods=['POST'])
def kitchen_reject_order():
    """Kitchen staff rejects an order due to unavailability"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        reason = data.get('reason', 'Items currently unavailable')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Update order status to rejected
        order.status = 'rejected'
        order.rejection_reason = reason
        order.rejected_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify customer about rejection
        notify_customer_order_rejected(order, reason)
        
        # Log for real-time updates
        logger.info(f"❌ KITCHEN REJECTED: Order #{order.id} - Reason: {reason}")
        
        return jsonify({
            'success': True,
            'message': 'Order rejected. Customer notified.',
            'order_status': 'rejected'
        })
        
    except Exception as e:
        logger.error(f"Error rejecting order: {e}")
        return jsonify({'error': str(e)}), 500

def notify_customer_make_deposit(order):
    """Notify customer to make deposit after kitchen accepts order"""
    try:
        from bot_minimal import send_message
        
        message = f"""
✅ *Order Accepted by Kitchen!*

🏪 Flavour Cafe | E.Fabrica has accepted your order

📋 *Order #*{order.id}
💰 *Total:* {order.total_amount:.2f} ETB
💳 *Deposit Required:* {order.deposit_amount:.2f} ETB (50%)

⏰ *Please make deposit within 30 minutes*

💳 *Payment Methods:*
• CBE Birr: 1000-xxxx-xxxx  
• M-Pesa: +251-911-123456
• Bank Transfer: CBE Account 10001234567890

📸 Upload payment screenshot after transfer
🕐 Deadline: {(datetime.utcnow()).strftime('%I:%M %p')} + 30 minutes

Your order will be prepared once payment is verified!
        """
        
        if order.telegram_user_id:
            send_message(order.telegram_user_id, message, parse_mode='Markdown')
            logger.info(f"Deposit notification sent to customer {order.customer_name}")
        
    except Exception as e:
        logger.error(f"Error notifying customer for deposit: {e}")

def notify_customer_order_rejected(order, reason):
    """Notify customer when kitchen rejects order"""
    try:
        from bot_minimal import send_message
        
        message = f"""
❌ *Order Not Available*

🏪 Flavour Cafe | E.Fabrica cannot fulfill your order

📋 *Order #*{order.id}
⚠️ *Reason:* {reason}

We apologize for the inconvenience. Please try:
• Ordering different items from our menu
• Contacting us directly: +251-911-123456
• Trying again later

Thank you for understanding!
        """
        
        if order.telegram_user_id:
            send_message(order.telegram_user_id, message, parse_mode='Markdown')
            logger.info(f"Rejection notification sent to customer {order.customer_name}")
        
    except Exception as e:
        logger.error(f"Error notifying customer about rejection: {e}")

def notify_kitchen_start_preparation_realtime(order):
    """Real-time notification to kitchen dashboard when payment is verified"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Kitchen staff use web dashboard - log for real-time updates
        logger.info(f"🚨 PAYMENT VERIFIED: Order #{order.id} - START PREPARATION!")
        logger.info(f"Customer: {order.customer_name}, Total: {order.total_amount:.2f} ETB")
        logger.info(f"Kitchen dashboard will show 'Start Preparation' status")
        
        # Update order status for kitchen dashboard
        order.status = 'confirmed'
        order.payment_verified_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Kitchen can now start preparing Order #{order.id}")
        
    except Exception as e:
        logger.error(f"Error updating kitchen preparation status: {e}")

def handle_kitchen_acceptance(order_id):
    """Handle kitchen acceptance workflow - called from kitchen_routes.py"""
    try:
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found for kitchen acceptance")
            return
        
        # Calculate deposit amount (50% of total)
        deposit_amount = order.total_amount * 0.5
        order.deposit_amount = deposit_amount
        order.kitchen_accepted_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify customer to make deposit
        notify_customer_make_deposit(order)
        
        # Log for real-time updates
        logger.info(f"🍽️ KITCHEN ACCEPTED: Order #{order.id} - Deposit required: {deposit_amount:.2f} ETB")
        logger.info(f"Customer {order.customer_name} notified to make payment")
        
    except Exception as e:
        logger.error(f"Error in handle_kitchen_acceptance: {e}")

# Register blueprint
app.register_blueprint(enhanced_kitchen_workflow)