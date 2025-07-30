"""
Enhanced Order Workflow System
Handles the complete order flow from kitchen availability confirmation to payment auto-approval
"""

import logging
from datetime import datetime
from flask import current_app
from models import Order, AdminUser
from bot_minimal import send_message
from config import Config

logger = logging.getLogger(__name__)

def notify_customer_kitchen_available(order_id):
    """Notify customer that kitchen confirmed availability and request payment"""
    try:
        from app import db
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
            
        # Send payment notification to customer
        message = f"✅ *Order Available!*\n\n"
        message += f"🍽️ **Order #{order.id}**\n"
        message += f"👨‍🍳 Kitchen confirmed all items are available\n"
        message += f"💰 **Total Amount:** {order.total_amount:.0f} ETB\n\n"
        message += f"💳 **Please make payment to proceed:**\n"
        message += f"• Method: {order.payment_method}\n"
        
        if order.payment_method == "Bank Transfer":
            message += f"• Bank: Commercial Bank of Ethiopia\n"
            message += f"• Account: 1000123456789\n"
            message += f"• Name: ET-FOOD Restaurant\n\n"
        elif order.payment_method == "Mobile Money":
            message += f"• Mobile Money: 0911-123456\n"
            message += f"• Name: ET-FOOD Restaurant\n\n"
        
        message += f"📱 After payment, upload receipt image\n"
        message += f"⏰ Kitchen will start preparation automatically"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "💳 Upload Payment Receipt",
                        "callback_data": f"upload_payment_{order.id}"
                    }
                ]
            ]
        }
        
        if order.telegram_user_id:
            send_message(order.telegram_user_id, message, keyboard, "Markdown")
            logger.info(f"Payment notification sent to customer {order.telegram_user_id} for order {order_id}")
            return True
        else:
            logger.warning(f"No telegram_user_id for order {order_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error notifying customer about kitchen availability: {e}")
        return False

def auto_approve_payment_and_start_kitchen(order_id):
    """Auto-approve payment and notify kitchen to start preparation"""
    try:
        from app import db
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
            
        # Update order status to confirmed (payment approved)
        order.status = 'confirmed'
        order.payment_verified = True
        order.payment_verified_at = datetime.utcnow()
        db.session.commit()
        
        # Send confirmation to customer
        customer_message = f"✅ *Payment Approved!*\n\n"
        customer_message += f"🍽️ **Order #{order.id}**\n"
        customer_message += f"💰 Amount: {order.total_amount:.0f} ETB\n"
        customer_message += f"✅ Payment verified successfully\n\n"
        customer_message += f"👨‍🍳 **Kitchen is now preparing your order**\n"
        customer_message += f"⏰ Estimated preparation time: 15-20 minutes\n"
        customer_message += f"📱 You'll receive updates as your order progresses"
        
        if order.telegram_user_id:
            send_message(order.telegram_user_id, customer_message, None, "Markdown")
        
        # Notify kitchen to start preparation
        admin_message = f"🔔 *START PREPARATION*\n\n"
        admin_message += f"✅ **Payment Approved for Order #{order.id}**\n"
        admin_message += f"👤 Customer: {order.customer_name}\n"
        admin_message += f"📞 Phone: {order.customer_phone}\n"
        admin_message += f"💰 Amount: {order.total_amount:.0f} ETB\n"
        admin_message += f"💳 Method: {order.payment_method}\n\n"
        admin_message += f"👨‍🍳 **Action Required:**\n"
        admin_message += f"• Start preparing the order immediately\n"
        admin_message += f"• Update status when ready for delivery\n\n"
        admin_message += f"🔥 Kitchen can begin preparation now!"
        
        # Send to all active admins
        admins = AdminUser.query.filter_by(is_active=True).all()
        for admin in admins:
            if hasattr(admin, 'telegram_user_id') and admin.telegram_user_id:
                send_message(admin.telegram_user_id, admin_message, None, "Markdown")
        
        logger.info(f"Auto-approved payment and notified kitchen for order {order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error auto-approving payment for order {order_id}: {e}")
        return False

def handle_kitchen_availability_response(order_id, is_available=True, reason=None):
    """Handle kitchen staff response about order availability"""
    try:
        from app import db
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found")
            return False
            
        if is_available:
            # Kitchen confirmed availability - notify customer for payment
            order.kitchen_confirmed = True
            order.kitchen_confirmed_at = datetime.utcnow()
            db.session.commit()
            
            # Send payment notification to customer
            notify_customer_kitchen_available(order_id)
            
            logger.info(f"Kitchen confirmed availability for order {order_id}")
            return True
        else:
            # Kitchen cannot fulfill order - notify customer
            order.status = 'cancelled'
            order.cancellation_reason = reason or "Items not available"
            order.cancelled_at = datetime.utcnow()
            db.session.commit()
            
            # Notify customer about unavailability
            message = f"❌ *Order Unavailable*\n\n"
            message += f"🍽️ **Order #{order.id}**\n"
            message += f"😔 Unfortunately, some items are currently unavailable\n\n"
            if reason:
                message += f"📝 **Reason:** {reason}\n\n"
            message += f"💰 No payment required\n"
            message += f"🔄 Please try again later or modify your order\n"
            message += f"📞 Contact us for assistance: +251-911-123456"
            
            if order.telegram_user_id:
                send_message(order.telegram_user_id, message, None, "Markdown")
            
            logger.info(f"Kitchen marked order {order_id} as unavailable: {reason}")
            return True
            
    except Exception as e:
        logger.error(f"Error handling kitchen availability response: {e}")
        return False