"""
Real-time Admin Notification System
Handles instant notifications to admins when customers place orders
"""

import os
import logging
import json
from datetime import datetime
from models import Order, AdminUser
from app import db
from bot_minimal import send_message_to_admin

logger = logging.getLogger(__name__)

def notify_admin_new_order(order_id):
    """Send real-time notification to admin when new order is placed"""
    try:
        from app import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            # Log the order for kitchen dashboard
            logger.info(f"🔔 NEW ORDER RECEIVED - Order #{order.id}")
            logger.info(f"Customer: {order.customer_name}, Phone: {order.customer_phone}")
            logger.info(f"Total: {order.total_amount:.2f} ETB, Payment: {order.payment_method}")
            
            # Create comprehensive order notification for admin
            message = f"🔔 *NEW ORDER RECEIVED*\n\n"
            message += f"📋 **Order Details:**\n"
            message += f"• Order ID: #{order.id}\n"
            message += f"• Time: {order.created_at.strftime('%I:%M %p')}\n"
            message += f"• Total: {order.total_amount:.2f} ETB\n"
            message += f"• Payment: {order.payment_method}\n\n"
            
            message += f"👤 **Customer Information:**\n"
            message += f"• Name: {order.customer_name}\n"
            message += f"• Phone: {order.customer_phone}\n"
            message += f"• Address: {order.customer_address}\n\n"
            
            # Add order items
            if order.items:
                message += f"🛒 **Order Items:**\n"
                try:
                    # Handle both string and already parsed JSON
                    items_data = order.items if isinstance(order.items, list) else json.loads(order.items)
                    for item in items_data:
                        message += f"• {item['name']} x{item['quantity']} - {item['price']:.2f} ETB\n"
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    message += f"• Order items (details unavailable)\n"
            
            # Try to send to admins via Telegram if BOT_TOKEN is configured
            try:
                from config import Config
                if Config.BOT_TOKEN and Config.BOT_TOKEN != 'your_bot_token_here':
                    admins = AdminUser.query.filter_by(is_active=True).all()
                    if admins:
                        for admin in admins:
                            if admin.telegram_user_id:
                                try:
                                    from bot_minimal import send_message
                                    send_message(admin.telegram_user_id, message, parse_mode="Markdown")
                                    logger.info(f"New order notification sent to admin {admin.username}")
                                except Exception as e:
                                    logger.error(f"Failed to send notification to admin {admin.username}: {e}")
                    else:
                        logger.warning("No active admins found to notify")
                else:
                    logger.info("BOT_TOKEN not configured - notification logged for kitchen dashboard")
            except Exception as e:
                logger.error(f"Error sending telegram notification: {e}")
            
            logger.info(f"New order #{order_id} notification processed")
            return True
            
    except Exception as e:
        logger.error(f"Error notifying admin about new order: {e}")
        return False

def handle_admin_order_confirmation(admin_telegram_id, order_id):
    """Handle admin order confirmation and trigger driver search"""
    try:
        from app import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            if order.status != 'pending':
                send_message_to_admin(admin_telegram_id, 
                    f"⚠️ Order #{order_id} is already {order.status.upper()}")
                return False
            
            # Update order status to confirmed
            order.status = 'confirmed'
            order.confirmed_at = datetime.utcnow()
            order.confirmed_by = admin_telegram_id
            
            db.session.commit()
            
            # Send confirmation to admin
            send_message_to_admin(admin_telegram_id,
                f"✅ Order #{order_id} confirmed!\n"
                f"🔍 System is now searching for nearby drivers...\n"
                f"📱 You will be notified when a driver accepts the order.")
            
            # Trigger driver search (import here to avoid circular imports)
            from complete_order_workflow import process_new_order
            process_new_order(order_id)
            
            logger.info(f"Order {order_id} confirmed by admin {admin_telegram_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error handling admin order confirmation: {e}")
        return False

def handle_admin_order_rejection(admin_telegram_id, order_id, reason=None):
    """Handle admin order rejection"""
    try:
        from app import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            if order.status != 'pending':
                send_message_to_admin(admin_telegram_id,
                    f"⚠️ Order #{order_id} is already {order.status.upper()}")
                return False
            
            # Update order status to rejected
            order.status = 'rejected'
            order.rejected_at = datetime.utcnow()
            order.rejected_by = admin_telegram_id
            if reason:
                order.rejection_reason = reason
            
            db.session.commit()
            
            # Send confirmation to admin
            send_message_to_admin(admin_telegram_id,
                f"❌ Order #{order_id} rejected.\n"
                f"📞 Customer {order.customer_name} has been notified.")
            
            # Notify customer about rejection
            from bot_minimal import send_message
            customer_message = f"😔 *Order Rejected*\n\n"
            customer_message += f"📋 Order #{order_id}\n"
            customer_message += f"❌ Your order has been rejected by the restaurant.\n"
            if reason:
                customer_message += f"📝 Reason: {reason}\n"
            customer_message += f"\n📞 Contact us: +251-911-234567\n"
            customer_message += f"🙏 We apologize for any inconvenience."
            
            send_message(order.telegram_user_id, customer_message)
            
            logger.info(f"Order {order_id} rejected by admin {admin_telegram_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error handling admin order rejection: {e}")
        return False

def notify_admin_driver_assignment(order_id, driver_name):
    """Notify admin when driver accepts order"""
    try:
        from app import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            message = f"🚚 *Driver Assigned*\n\n"
            message += f"📋 Order #{order_id}\n"
            message += f"👤 Driver: {driver_name}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Customer Phone: {order.customer_phone}\n"
            message += f"🕐 Assignment Time: {datetime.now().strftime('%I:%M %p')}\n\n"
            message += f"🎯 **Order Status:** ASSIGNED\n"
            message += f"📱 Monitor progress in admin dashboard"
            
            # Send to all admins
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                if admin.telegram_user_id:
                    send_message_to_admin(admin.telegram_user_id, message)
            
            logger.info(f"Driver assignment notification sent for order {order_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error notifying admin about driver assignment: {e}")
        return False

def test_admin_notification_system():
    """Test the admin notification system"""
    try:
        from app import app
        
        # Find a test order
        with app.app_context():
            order = Order.query.filter_by(status='pending').first()
            if not order:
                logger.error("No pending orders found for testing")
                return False
            
            logger.info(f"Testing admin notification system with Order #{order.id}")
            
            # Test notification
            result = notify_admin_new_order(order.id)
            
            if result:
                logger.info("✅ Admin notification system test successful")
                return True
            else:
                logger.error("❌ Admin notification system test failed")
                return False
                
    except Exception as e:
        logger.error(f"Error testing admin notification system: {e}")
        return False

if __name__ == "__main__":
    # Test the admin notification system
    test_admin_notification_system()