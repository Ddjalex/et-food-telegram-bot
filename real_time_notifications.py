"""
Real-time Notification System for ET-FOOD
Handles Telegram notifications between admin, kitchen staff, and customers
"""

import requests
import logging
import os
from models import db, KitchenStaff, AdminUser

logger = logging.getLogger(__name__)

def send_telegram_notification(telegram_user_id, message, bot_token=None):
    """Send notification via Telegram bot"""
    try:
        # Use main bot token for notifications
        if not bot_token:
            bot_token = os.environ.get('BOT_TOKEN', os.environ.get('ETFASTFOOD_BOT_TOKEN'))
            
        if not bot_token or bot_token == 'your_bot_token_here':
            logger.warning("Bot token not configured for notifications")
            return False
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': telegram_user_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"Notification sent successfully to {telegram_user_id}")
            return True
        else:
            logger.error(f"Failed to send notification: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

def notify_kitchen_staff_payment_verified(order):
    """Notify kitchen staff that payment has been verified and they should start preparing"""
    try:
        logger.info(f"Notifying kitchen staff for order #{order.id}")
        
        # Get kitchen staff for this restaurant
        kitchen_staff = KitchenStaff.query.filter_by(
            restaurant_id=order.restaurant_id,
            is_active=True
        ).all()
        
        if not kitchen_staff:
            logger.warning(f"No active kitchen staff found for restaurant {order.restaurant_id}")
            return False
        
        # Create notification message
        message = f"💳 *PAYMENT VERIFIED - START PREPARING*\n\n"
        message += f"🆔 *Order*: #{order.id}\n"
        message += f"👤 *Customer*: {order.customer_name}\n"
        message += f"📞 *Phone*: {order.customer_phone or 'N/A'}\n"
        message += f"💰 *Amount*: {order.total_amount:.2f} ETB\n"
        message += f"📍 *Address*: {order.customer_address or order.delivery_address or 'N/A'}\n\n"
        
        # Add order items
        if order.items:
            message += f"🍽️ *Order Items*:\n"
            items_list = order.items.split(',') if isinstance(order.items, str) else order.items
            for i, item in enumerate(items_list[:5], 1):  # Show first 5 items
                message += f"{i}. {item.strip()}\n"
            if len(items_list) > 5:
                message += f"... and {len(items_list) - 5} more items\n"
        
        message += f"\n🍳 *ACTION REQUIRED*: Start preparing this order now!\n"
        message += f"⏰ *Target Time*: 15-20 minutes\n\n"
        message += f"Click /kitchen to access kitchen dashboard"
        
        notifications_sent = []
        for staff in kitchen_staff:
            if staff.telegram_user_id:
                success = send_telegram_notification(staff.telegram_user_id, message)
                if success:
                    notifications_sent.append(f"Kitchen: {staff.name}")
                    logger.info(f"Notified kitchen staff: {staff.name} ({staff.telegram_user_id})")
            else:
                logger.warning(f"Kitchen staff {staff.name} has no telegram_user_id")
        
        return notifications_sent
        
    except Exception as e:
        logger.error(f"Error notifying kitchen staff: {e}")
        return []

def notify_customer_payment_approved(order):
    """Notify customer that payment has been approved and order is being prepared"""
    try:
        logger.info(f"Notifying customer for order #{order.id}")
        
        if not order.telegram_user_id:
            logger.warning(f"Order #{order.id} has no telegram_user_id for customer notification")
            return False
        
        message = f"✅ *PAYMENT APPROVED*\n\n"
        message += f"🆔 *Order*: #{order.id}\n"
        message += f"💰 *Amount*: {order.total_amount:.2f} ETB\n"
        message += f"✅ *Status*: Payment Verified\n\n"
        message += f"🍳 *Good News*: Your order is now being prepared!\n"
        message += f"⏰ *Estimated Time*: 15-30 minutes\n"
        message += f"🚚 *Delivery*: We'll notify you when ready for delivery\n\n"
        message += f"Thank you for your order! 🙏"
        
        success = send_telegram_notification(order.telegram_user_id, message)
        if success:
            logger.info(f"Customer notification sent for order #{order.id}")
            return True
        else:
            logger.error(f"Failed to notify customer for order #{order.id}")
            return False
            
    except Exception as e:
        logger.error(f"Error notifying customer: {e}")
        return False

def notify_customer_order_preparing(order, kitchen_staff_name=None):
    """Notify customer that kitchen has started preparing their order"""
    try:
        logger.info(f"Notifying customer that order #{order.id} preparation started")
        
        if not order.telegram_user_id:
            logger.warning(f"Order #{order.id} has no telegram_user_id for customer notification")
            return False
        
        kitchen_name = kitchen_staff_name or "Our kitchen team"
        
        message = f"👨‍🍳 *ORDER PREPARATION STARTED*\n\n"
        message += f"🆔 *Order*: #{order.id}\n"
        message += f"👨‍🍳 *Chef*: {kitchen_name}\n"
        message += f"🍽️ *Status*: Now preparing your delicious food!\n\n"
        message += f"⏰ *Estimated Time*: 15-20 minutes\n"
        message += f"🔥 *Process*: Fresh ingredients, made with care\n"
        message += f"📱 *Tracking*: We'll update you when ready!\n\n"
        message += f"Get ready for an amazing meal! 😋"
        
        success = send_telegram_notification(order.telegram_user_id, message)
        if success:
            logger.info(f"Customer preparation notification sent for order #{order.id}")
            return True
        else:
            logger.error(f"Failed to notify customer about preparation for order #{order.id}")
            return False
            
    except Exception as e:
        logger.error(f"Error notifying customer about preparation: {e}")
        return False

def notify_admin_kitchen_started(order, kitchen_staff_name):
    """Notify admin that kitchen staff started preparing an order"""
    try:
        logger.info(f"Notifying admin that kitchen started preparing order #{order.id}")
        
        # Get restaurant admins
        admins = AdminUser.query.filter_by(
            restaurant_id=order.restaurant_id,
            is_active=True
        ).all()
        
        if not admins:
            logger.warning(f"No active admins found for restaurant {order.restaurant_id}")
            return False
        
        message = f"👨‍🍳 *KITCHEN UPDATE*\n\n"
        message += f"🆔 *Order*: #{order.id}\n"
        message += f"👤 *Customer*: {order.customer_name}\n"
        message += f"👨‍🍳 *Chef*: {kitchen_staff_name}\n"
        message += f"🍽️ *Status*: Preparation started\n"
        message += f"💰 *Amount*: {order.total_amount:.2f} ETB\n\n"
        message += f"✅ Kitchen team is now preparing the order\n"
        message += f"⏰ Expected completion: 15-20 minutes"
        
        notifications_sent = []
        for admin in admins:
            if hasattr(admin, 'telegram_user_id') and admin.telegram_user_id:
                success = send_telegram_notification(admin.telegram_user_id, message)
                if success:
                    notifications_sent.append(f"Admin: {admin.username}")
        
        return notifications_sent
        
    except Exception as e:
        logger.error(f"Error notifying admin about kitchen start: {e}")
        return []