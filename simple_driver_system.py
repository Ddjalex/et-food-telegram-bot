"""
Simple Driver Registration System
Clean and easy-to-use driver management
"""

import os
import logging
import requests
import json
from datetime import datetime
from flask import request, jsonify
from extensions import db
from models import Driver

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Driver Bot Configuration
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')

def send_simple_message(chat_id, text, keyboard=None):
    """Send a simple message to driver"""
    if not DRIVER_BOT_TOKEN:
        logger.warning("Driver bot token not configured")
        return False
    
    url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }
    
    if keyboard:
        data['reply_markup'] = json.dumps(keyboard)
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            logger.info(f"Message sent successfully to driver {chat_id}")
            return True
        else:
            logger.error(f"Failed to send message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def handle_driver_start(chat_id):
    """Handle /start command for driver bot - simplified version"""
    welcome_message = """
🚗 *Welcome to ET-FOOD Driver Bot*

To become a driver, please contact the admin directly.

📞 Contact admin for driver registration
📍 You must be approved by admin first
⚡ Once approved, you'll get access to delivery orders

*Current Status:* Not registered
*Next Step:* Contact admin for approval
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📞 Contact Admin",
                    "callback_data": "contact_admin"
                }
            ]
        ]
    }
    
    return send_simple_message(chat_id, welcome_message, keyboard)

def handle_approved_driver_start(chat_id, driver_name):
    """Handle /start for approved drivers"""
    welcome_message = f"""
🚗 *Welcome back, {driver_name}!*

You are an approved ET-FOOD driver.

📋 Available Actions:
• View pending orders
• Check your status
• Share your location
• View earnings

*Status:* ✅ Approved Driver
*Ready for orders:* Yes
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📋 My Orders",
                    "callback_data": "driver_orders"
                }
            ],
            [
                {
                    "text": "📍 Share Location",
                    "callback_data": "share_location"
                },
                {
                    "text": "📊 My Status",
                    "callback_data": "driver_status"
                }
            ]
        ]
    }
    
    return send_simple_message(chat_id, welcome_message, keyboard)

def send_order_notification(driver_telegram_id, order_data):
    """Send simple order notification to driver"""
    message = f"""
🚚 *New Order Available*

📋 Order #{order_data['id']}
👤 Customer: {order_data['customer_name']}
📞 Phone: {order_data['customer_phone']}
💰 Total: {order_data['total_amount']:.2f} ETB
📍 Distance: {order_data.get('distance', 'N/A')} km

⚡ *Quick Action Required*
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Accept Order",
                    "callback_data": f"accept_order_{order_data['id']}"
                },
                {
                    "text": "❌ Decline",
                    "callback_data": f"decline_order_{order_data['id']}"
                }
            ]
        ]
    }
    
    return send_simple_message(driver_telegram_id, message, keyboard)

def handle_contact_admin(chat_id):
    """Handle contact admin request"""
    message = """
📞 *Contact Admin for Driver Registration*

Please contact the restaurant admin directly:

📱 Phone: +251-XXX-XXX-XXX
💬 Or ask admin to add you through admin panel

*What admin needs:*
• Your name
• Your phone number
• Your vehicle type
• Your location

Admin will approve you and give you access to orders.
"""
    
    return send_simple_message(chat_id, message)

def notify_driver_approval(driver_telegram_id, driver_name):
    """Notify driver of approval - simple version"""
    message = f"""
🎉 *Congratulations {driver_name}!*

You have been approved as an ET-FOOD driver!

✅ *You can now:*
• Receive delivery orders
• Earn money from deliveries
• Track your earnings

📍 *Important:* Share your location to receive nearby orders

*Status:* ✅ Approved Driver
*Ready for orders:* Yes
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Share Location Now",
                    "callback_data": "share_location"
                }
            ],
            [
                {
                    "text": "📋 View Orders",
                    "callback_data": "driver_orders"
                }
            ]
        ]
    }
    
    return send_simple_message(driver_telegram_id, message, keyboard)

def handle_driver_callback(callback_data, chat_id):
    """Handle driver bot callbacks - simplified"""
    if callback_data == "contact_admin":
        return handle_contact_admin(chat_id)
    elif callback_data == "driver_orders":
        return send_driver_orders(chat_id)
    elif callback_data == "driver_status":
        return send_driver_status(chat_id)
    elif callback_data == "share_location":
        return request_location_sharing(chat_id)
    elif callback_data.startswith("accept_order_"):
        order_id = callback_data.split("_")[-1]
        return handle_order_acceptance(chat_id, order_id)
    elif callback_data.startswith("decline_order_"):
        order_id = callback_data.split("_")[-1]
        return handle_order_decline(chat_id, order_id)
    
    return False

def send_driver_orders(chat_id):
    """Send driver's current orders"""
    # Check if driver is approved
    driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
    if not driver or not driver.is_approved:
        return send_simple_message(chat_id, "❌ You are not an approved driver yet. Contact admin first.")
    
    # Get driver's orders
    orders = db.session.query(Order).filter_by(driver_id=driver.id, status='out_for_delivery').all()
    
    if not orders:
        message = "📋 *No Active Orders*\n\nYou have no active deliveries right now.\nWait for new orders or check your status."
    else:
        message = "📋 *Your Active Orders*\n\n"
        for order in orders:
            message += f"Order #{order.id} - {order.customer_name}\n"
            message += f"💰 {order.total_amount:.2f} ETB\n"
            message += f"📞 {order.customer_phone}\n\n"
    
    return send_simple_message(chat_id, message)

def send_driver_status(chat_id):
    """Send driver status"""
    driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
    if not driver:
        return send_simple_message(chat_id, "❌ You are not registered as a driver.")
    
    if not driver.is_approved:
        return send_simple_message(chat_id, "⏳ Your driver application is pending admin approval.")
    
    status = "🟢 Online" if driver.is_active else "🔴 Offline"
    available = "✅ Available" if driver.is_available else "❌ Busy"
    
    message = f"""
📊 *Driver Status*

👤 Name: {driver.name}
📱 Phone: {driver.phone_number}
🚗 Vehicle: {driver.vehicle_type}
📍 Status: {status}
🎯 Available: {available}

*Total Deliveries:* {len(driver.orders) if driver.orders else 0}
*Account Status:* ✅ Approved
"""
    
    return send_simple_message(chat_id, message)

def request_location_sharing(chat_id):
    """Request location sharing from driver"""
    message = """
📍 *Share Your Location*

Please share your current location so we can:
• Send you nearby orders
• Calculate delivery distances
• Track your availability

Use the location button in Telegram to share your GPS coordinates.
"""
    
    return send_simple_message(chat_id, message)

def handle_order_acceptance(chat_id, order_id):
    """Handle order acceptance"""
    try:
        # Find the driver
        driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
        if not driver or not driver.is_approved:
            return send_simple_message(chat_id, "❌ You are not an approved driver.")
        
        # Find the order
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            return send_simple_message(chat_id, "❌ Order not found.")
        
        if order.driver_id:
            return send_simple_message(chat_id, "❌ This order has already been assigned to another driver.")
        
        # Assign order to driver
        order.driver_id = driver.id
        order.status = 'out_for_delivery'
        db.session.commit()
        
        # Send confirmation
        message = f"""
✅ *Order Accepted!*

📋 Order #{order.id}
👤 Customer: {order.customer_name}
📞 Phone: {order.customer_phone}
📍 Address: {order.customer_address}
💰 Total: {order.total_amount:.2f} ETB

*Next Steps:*
• Pick up the order from restaurant
• Deliver to customer
• Mark as delivered when complete
"""
        
        return send_simple_message(chat_id, message)
        
    except Exception as e:
        logger.error(f"Error handling order acceptance: {e}")
        return send_simple_message(chat_id, "❌ Error accepting order. Please try again.")

def handle_order_decline(chat_id, order_id):
    """Handle order decline"""
    message = "❌ Order declined. We'll find another driver for this order."
    return send_simple_message(chat_id, message)