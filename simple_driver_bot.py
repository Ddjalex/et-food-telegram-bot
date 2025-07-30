"""
Simple Driver Bot System
Clean and easy-to-use driver management - no complex registration
"""

import os
import logging
import requests
import json
from flask import request, jsonify
from app import db
from models import Driver, Order

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')

def send_simple_driver_message(chat_id, text, keyboard=None):
    """Send simple message to driver"""
    if not DRIVER_BOT_TOKEN:
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
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def handle_simple_driver_start(chat_id):
    """Handle /start command - simple version"""
    from app import app
    
    with app.app_context():
        driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
        
        if driver and driver.is_approved:
            # Approved driver
            return send_approved_driver_welcome(chat_id, driver)
        else:
            # Not approved
            return send_not_approved_message(chat_id)

def send_approved_driver_welcome(chat_id, driver):
    """Send welcome message to approved driver"""
    message = f"""
🚗 *Welcome {driver.name}!*

You are an approved ET-FOOD driver.

📋 *Available Actions:*
• Check orders
• Share location
• View status

*Status:* ✅ Approved Driver
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📋 My Orders", "callback_data": "my_orders"},
                {"text": "📍 Share Location", "callback_data": "share_location"}
            ],
            [
                {"text": "📊 My Status", "callback_data": "my_status"}
            ]
        ]
    }
    
    return send_simple_driver_message(chat_id, message, keyboard)

def send_not_approved_message(chat_id):
    """Send message to non-approved user"""
    message = """
🚗 *ET-FOOD Driver Bot*

To become a driver, contact the admin.

📞 *Contact admin for registration*
📍 *Admin must approve you first*

*Status:* Not approved
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📞 Contact Admin", "callback_data": "contact_admin"}
            ]
        ]
    }
    
    return send_simple_driver_message(chat_id, message, keyboard)

def handle_simple_callback(callback_data, chat_id):
    """Handle simple callbacks"""
    if callback_data == "my_orders":
        return send_driver_orders(chat_id)
    elif callback_data == "share_location":
        return request_location(chat_id)
    elif callback_data == "my_status":
        return send_driver_status(chat_id)
    elif callback_data == "contact_admin":
        return send_contact_admin_info(chat_id)
    elif callback_data.startswith("accept_"):
        order_id = callback_data.split("_")[1]
        return accept_order(chat_id, order_id)
    elif callback_data.startswith("decline_"):
        order_id = callback_data.split("_")[1]
        return decline_order(chat_id, order_id)
    
    return False

def send_driver_orders(chat_id):
    """Send driver's orders"""
    from app import app
    
    with app.app_context():
        driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
        if not driver or not driver.is_approved:
            return send_simple_driver_message(chat_id, "❌ You are not approved.")
        
        orders = Order.query.filter_by(driver_id=driver.id, status='out_for_delivery').all()
        
        if not orders:
            message = "📋 *No Active Orders*\n\nNo deliveries right now."
        else:
            message = "📋 *Your Orders*\n\n"
            for order in orders:
                message += f"#{order.id} - {order.customer_name}\n"
                message += f"💰 {order.total_amount:.2f} ETB\n\n"
        
        return send_simple_driver_message(chat_id, message)

def request_location(chat_id):
    """Request location from driver"""
    message = """
📍 *Share Your Location*

Please share your location for order assignments.

Use Telegram's location button to share your GPS coordinates.
"""
    
    return send_simple_driver_message(chat_id, message)

def send_driver_status(chat_id):
    """Send driver status"""
    from app import app
    
    with app.app_context():
        driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
        if not driver:
            return send_simple_driver_message(chat_id, "❌ Not registered.")
        
        if not driver.is_approved:
            return send_simple_driver_message(chat_id, "⏳ Waiting for approval.")
        
        status = "🟢 Active" if driver.is_active else "🔴 Inactive"
        available = "✅ Available" if driver.is_available else "❌ Busy"
        
        message = f"""
📊 *Driver Status*

👤 Name: {driver.name}
📱 Phone: {driver.phone_number}
📍 Status: {status}
🎯 Available: {available}

*Account:* ✅ Approved
"""
        
        return send_simple_driver_message(chat_id, message)

def send_contact_admin_info(chat_id):
    """Send admin contact info"""
    message = """
📞 *Contact Admin*

Ask admin to add you as a driver.

*What admin needs:*
• Your name
• Your phone number
• Your vehicle type

Admin will approve you for deliveries.
"""
    
    return send_simple_driver_message(chat_id, message)

def send_simple_order_notification(chat_id, order_data):
    """Send simple order notification"""
    message = f"""
🚚 *New Order*

Order #{order_data['id']}
👤 {order_data['customer_name']}
💰 {order_data['total_amount']:.2f} ETB

*Quick Action:*
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Accept", "callback_data": f"accept_{order_data['id']}"},
                {"text": "❌ Decline", "callback_data": f"decline_{order_data['id']}"}
            ]
        ]
    }
    
    return send_simple_driver_message(chat_id, message, keyboard)

def accept_order(chat_id, order_id):
    """Accept an order"""
    from app import app
    
    with app.app_context():
        driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
        order = Order.query.get(order_id)
        
        if not driver or not order:
            return send_simple_driver_message(chat_id, "❌ Error accepting order.")
        
        if order.driver_id:
            return send_simple_driver_message(chat_id, "❌ Order already assigned.")
        
        # Assign order
        order.driver_id = driver.id
        order.status = 'out_for_delivery'
        db.session.commit()
        
        message = f"""
✅ *Order Accepted*

Order #{order.id}
Customer: {order.customer_name}
Phone: {order.customer_phone}
Total: {order.total_amount:.2f} ETB

*Next:* Pick up and deliver the order
"""
        
        return send_simple_driver_message(chat_id, message)

def decline_order(chat_id, order_id):
    """Decline an order"""
    message = "❌ Order declined. Looking for another driver."
    return send_simple_driver_message(chat_id, message)

def notify_driver_approval(chat_id, driver_name):
    """Notify driver of approval"""
    message = f"""
🎉 *Approved!*

Congratulations {driver_name}!

You are now an ET-FOOD driver.

✅ *You can now:*
• Receive orders
• Earn money
• Track deliveries

📍 *Share your location to get orders*
"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📍 Share Location", "callback_data": "share_location"}
            ]
        ]
    }
    
    return send_simple_driver_message(chat_id, message, keyboard)