"""
Real-time notification system for ET-FOOD
Handles live notifications for driver approvals, payments, and order updates
"""

import logging
from flask import jsonify
from models import db, Driver, Order, AdminUser, Restaurant
from datetime import datetime
import requests
from config import Config

logger = logging.getLogger(__name__)

def send_telegram_notification(chat_id, message, keyboard=None):
    """Send Telegram notification"""
    if not Config.BOT_TOKEN or Config.BOT_TOKEN == 'your_bot_token_here':
        logger.warning("BOT_TOKEN not configured - notification not sent")
        return False
    
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    if keyboard:
        data["reply_markup"] = keyboard
    
    try:
        response = requests.post(url, json=data)
        result = response.json()
        if result.get("ok"):
            logger.info(f"Telegram notification sent successfully to {chat_id}")
            return True
        else:
            logger.error(f"Telegram notification failed: {result}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

def notify_restaurants_new_driver(driver_id):
    """Send real-time notification to all restaurant admins about new approved driver"""
    try:
        driver = Driver.query.get(driver_id)
        if not driver:
            return False
        
        # Get all active restaurant admins
        admins = AdminUser.query.filter_by(
            is_active=True,
            role='admin'
        ).all()
        
        notification_count = 0
        
        for admin in admins:
            try:
                # Construct notification message
                message = f"🚗 *NEW DRIVER APPROVED*\n\n"
                message += f"✅ **Driver**: {driver.name}\n"
                message += f"📱 **Phone**: {driver.phone_number}\n"
                message += f"🚙 **Vehicle**: {driver.vehicle_type.title()}\n"
                message += f"📍 **Status**: Available for deliveries\n"
                message += f"⏰ **Approved**: {datetime.utcnow().strftime('%H:%M')}\n\n"
                message += f"🎯 **This driver is now available for your restaurant's delivery orders!**\n"
                message += f"They will appear in your driver assignment list for new orders."
                
                # Create keyboard for quick actions
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "👥 View All Drivers",
                                "callback_data": "view_drivers"
                            },
                            {
                                "text": "📊 Admin Dashboard",
                                "callback_data": "admin_dashboard"
                            }
                        ]
                    ]
                }
                
                # Send notification if admin has Telegram ID
                if admin.telegram_user_id:
                    success = send_telegram_notification(
                        admin.telegram_user_id, 
                        message, 
                        keyboard
                    )
                    if success:
                        notification_count += 1
                        logger.info(f"Sent driver approval notification to admin {admin.username}")
                
            except Exception as e:
                logger.error(f"Error sending notification to admin {admin.username}: {e}")
        
        logger.info(f"Sent driver approval notifications to {notification_count} restaurant admins")
        return notification_count > 0
        
    except Exception as e:
        logger.error(f"Error in notify_restaurants_new_driver: {e}")
        return False

def notify_payment_verification_needed(order_id):
    """Send real-time notification to restaurant admin about payment verification needed"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return False
        
        # Get restaurant admin
        admin = AdminUser.query.filter_by(
            restaurant_id=order.restaurant_id,
            role='admin',
            is_active=True
        ).first()
        
        if not admin or not admin.telegram_user_id:
            logger.warning(f"No admin with Telegram ID found for restaurant {order.restaurant_id}")
            return False
        
        # Construct payment verification message
        message = f"💳 *PAYMENT VERIFICATION NEEDED*\n\n"
        message += f"🆔 **Order**: #{order.id}\n"
        message += f"👤 **Customer**: {order.customer_name}\n"
        message += f"📱 **Phone**: {order.customer_phone}\n"
        message += f"💰 **Amount**: {order.total_amount:.2f} ETB\n"
        message += f"💳 **Payment Method**: {order.payment_method}\n"
        
        if order.transaction_id:
            message += f"🔢 **Transaction ID**: {order.transaction_id}\n"
        
        message += f"⏰ **Order Time**: {order.created_at.strftime('%H:%M')}\n\n"
        message += f"📸 **Payment screenshot uploaded!**\n"
        message += f"🔍 **Action Required**: Please verify the payment screenshot in your admin dashboard."
        
        # Create keyboard for quick actions
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Verify Payment",
                        "callback_data": f"verify_payment_{order.id}"
                    },
                    {
                        "text": "❌ Reject Payment",
                        "callback_data": f"reject_payment_{order.id}"
                    }
                ],
                [
                    {
                        "text": "📊 Admin Dashboard",
                        "callback_data": "admin_dashboard"
                    }
                ]
            ]
        }
        
        # Send notification
        success = send_telegram_notification(
            admin.telegram_user_id,
            message,
            keyboard
        )
        
        if success:
            logger.info(f"Sent payment verification notification for order {order_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error in notify_payment_verification_needed: {e}")
        return False

def notify_order_status_change(order_id, new_status, admin_action=True):
    """Send real-time notification about order status changes"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return False
        
        # Determine message based on status
        status_messages = {
            'confirmed': '✅ Order Confirmed',
            'preparing': '👨‍🍳 Preparing Your Order',
            'ready': '🍽️ Order Ready for Pickup',
            'out_for_delivery': '🚚 Out for Delivery',
            'delivered': '✅ Order Delivered'
        }
        
        message = f"📦 *{status_messages.get(new_status, 'Order Update')}*\n\n"
        message += f"🆔 **Order**: #{order.id}\n"
        message += f"👤 **Customer**: {order.customer_name}\n"
        message += f"💰 **Amount**: {order.total_amount:.2f} ETB\n"
        message += f"⏰ **Updated**: {datetime.utcnow().strftime('%H:%M')}\n\n"
        
        if new_status == 'confirmed':
            message += "✅ **Payment verified successfully!**\nYour order is now confirmed and will be prepared shortly."
        elif new_status == 'preparing':
            message += "👨‍🍳 **Kitchen started preparing your order!**\nEstimated completion: 15-30 minutes."
        elif new_status == 'ready':
            message += "🍽️ **Your order is ready!**\nWaiting for driver assignment."
        elif new_status == 'out_for_delivery':
            message += "🚚 **Driver assigned!**\nYour order is on the way."
        elif new_status == 'delivered':
            message += "✅ **Order delivered successfully!**\nThank you for choosing ET-FOOD!"
        
        # Send to customer if they have telegram_user_id
        if hasattr(order, 'telegram_user_id') and order.telegram_user_id:
            send_telegram_notification(order.telegram_user_id, message)
        
        # Also send to restaurant admin if admin_action is False (system update)
        if not admin_action:
            admin = AdminUser.query.filter_by(
                restaurant_id=order.restaurant_id,
                role='admin',
                is_active=True
            ).first()
            
            if admin and admin.telegram_user_id:
                admin_message = f"📊 *ORDER STATUS UPDATE*\n\n"
                admin_message += f"🆔 **Order**: #{order.id}\n"
                admin_message += f"📊 **Status**: {new_status.replace('_', ' ').title()}\n"
                admin_message += f"👤 **Customer**: {order.customer_name}\n"
                admin_message += f"⏰ **Updated**: {datetime.utcnow().strftime('%H:%M')}"
                
                send_telegram_notification(admin.telegram_user_id, admin_message)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in notify_order_status_change: {e}")
        return False