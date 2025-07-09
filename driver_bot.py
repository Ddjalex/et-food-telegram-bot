"""
Driver Bot - Telegram bot for delivery drivers
Handles order assignments, acceptance/rejection, and provides mini web interface
"""

import os
import logging
import requests
import json
from datetime import datetime
from flask import request, jsonify
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Driver Bot Configuration
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')
DRIVER_WEBHOOK_URL = f"{os.environ.get('REPLIT_DEV_DOMAIN', 'localhost')}/driver-webhook"

def send_driver_message(chat_id, text, keyboard=None, parse_mode=None):
    """Send a message to Telegram using driver bot"""
    url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode or 'Markdown'
    }
    
    if keyboard:
        data['reply_markup'] = json.dumps(keyboard)
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            logger.info(f"Message sent successfully to driver {chat_id}")
        else:
            logger.error(f"Failed to send message: {response.text}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

def notify_driver_order_assignment(driver_telegram_id, order_data):
    """Notify driver about new order assignment with mini web interface"""
    try:
        # Calculate distance (mock calculation for demo)
        restaurant_coords = (9.145, 40.489658)  # Restaurant location
        customer_coords = (order_data.get('location_lat', 9.165), order_data.get('location_lng', 40.510))
        distance = calculate_distance(restaurant_coords, customer_coords)
        
        message = f"🚚 *New Delivery Request*\n\n"
        message += f"📋 Order #{order_data['id']}\n"
        message += f"🏪 Restaurant: ET-FOOD Kitchen\n"
        message += f"👤 Customer: {order_data['customer_name']}\n"
        message += f"📞 Phone: {order_data['customer_phone']}\n"
        message += f"📍 Distance: {order_data.get('distance', distance):.1f} km\n"
        message += f"💰 Total: {order_data['total_amount']:.2f} ETB\n"
        message += f"💳 Payment: {order_data.get('payment_method', 'Not specified')}\n"
        message += f"🕒 Order Time: {order_data.get('created_at', 'Just now')}\n\n"
        message += f"⚡ *First to accept gets the order!*\n"
        message += f"📱 Open driver panel for full details or use quick actions below."
        
        # Create inline keyboard with WebApp
        webapp_url = f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/driver-panel?order_id={order_data['id']}&driver_id={driver_telegram_id}"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📱 Open Driver Panel",
                        "web_app": {"url": webapp_url}
                    }
                ],
                [
                    {
                        "text": "✅ Quick Accept",
                        "callback_data": f"driver_accept_{order_data['id']}"
                    },
                    {
                        "text": "❌ Quick Reject", 
                        "callback_data": f"driver_reject_{order_data['id']}"
                    }
                ],
                [
                    {
                        "text": "📍 Share Location",
                        "callback_data": f"driver_location_{order_data['id']}"
                    }
                ]
            ]
        }
        
        send_driver_message(driver_telegram_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error notifying driver: {e}")

def calculate_distance(coord1, coord2):
    """Calculate distance between two coordinates (simplified)"""
    import math
    
    lat1, lng1 = coord1
    lat2, lng2 = coord2
    
    # Convert to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Earth's radius in kilometers
    
    return c * r

def handle_driver_callback(callback_query):
    """Handle driver bot callback queries"""
    try:
        callback_data = callback_query.get('data', '')
        chat_id = callback_query['from']['id']
        message_id = callback_query['message']['message_id']
        
        if callback_data.startswith('driver_accept_'):
            order_id = callback_data.split('_')[2]
            handle_order_acceptance(chat_id, order_id, message_id)
            
        elif callback_data.startswith('driver_reject_'):
            order_id = callback_data.split('_')[2]
            handle_order_rejection(chat_id, order_id, message_id)
            
        elif callback_data.startswith('driver_location_'):
            order_id = callback_data.split('_')[2]
            request_driver_location_sharing(chat_id, order_id)
            
        elif callback_data.startswith('call_restaurant_'):
            send_driver_message(chat_id, "📞 *Restaurant Contact*\n\nET-FOOD Kitchen\nPhone: +251-911-123-456\n\nPlease call to coordinate order pickup.")
            
        elif callback_data.startswith('call_customer_'):
            order_id = callback_data.split('_')[2]
            from models import Order
            order = Order.query.get(order_id)
            if order:
                send_driver_message(chat_id, f"📞 *Customer Contact*\n\nCustomer: {order.customer_name}\nPhone: {order.customer_phone}\n\nPlease call to coordinate delivery.")
                
        elif callback_data == 'contact_support':
            send_driver_message(chat_id, "📞 *Support Contact*\n\nET-FOOD Support\nPhone: +251-911-123-456\nEmail: support@et-food.com\n\nContact us for any assistance!")
            
        elif callback_data == 'request_location':
            send_location_request(chat_id)
            
        elif callback_data == 'enable_live_location':
            send_live_location_instructions(chat_id)
            
        elif callback_data.startswith('share_location_'):
            send_location_request(chat_id)
            
        elif callback_data.startswith('pickup_complete_'):
            order_id = callback_data.split('_')[2]
            handle_pickup_complete(chat_id, order_id)
            
        # Answer callback query
        answer_callback_query(callback_query['id'], "Action processed!")
        
    except Exception as e:
        logger.error(f"Error handling driver callback: {e}")

def send_location_request(chat_id):
    """Send location request message to driver"""
    message = "📍 *Location Sharing Required*\n\n"
    message += "Please share your current location to:\n"
    message += "✅ Receive order assignments\n"
    message += "✅ Enable distance-based matching\n"
    message += "✅ Allow admin monitoring\n\n"
    message += "Tap the 'Share Location' button below:"
    
    keyboard = {
        "reply_markup": {
            "keyboard": [
                [
                    {
                        "text": "📍 Share My Location",
                        "request_location": True
                    }
                ]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_live_location_instructions(chat_id):
    """Send live location sharing instructions"""
    message = "🔄 *Enable Live Location Sharing*\n\n"
    message += "For automatic location updates:\n\n"
    message += "1️⃣ Tap 'Share Location' in any chat\n"
    message += "2️⃣ Select 'Share Live Location'\n"
    message += "3️⃣ Choose duration (15 min, 1 hour, 8 hours)\n"
    message += "4️⃣ Tap 'Send'\n\n"
    message += "⚠️ **Important**: Keep live location ON during your shift!\n\n"
    message += "📍 This allows the system to:\n"
    message += "• Find nearby orders for you\n"
    message += "• Track delivery progress\n"
    message += "• Provide real-time updates to customers"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Share Location Now",
                    "callback_data": "request_location"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)
def handle_order_acceptance(driver_chat_id, order_id, message_id):
    """Handle order acceptance by driver"""
    try:
        from models import Order, Driver
        from extensions import db
        
        # Find driver by telegram ID
        driver = Driver.query.filter_by(telegram_user_id=driver_chat_id).first()
        if not driver:
            send_driver_message(driver_chat_id, "❌ Driver not found in system. Please contact admin.")
            return
            
        # Update order status
        order = Order.query.get(order_id)
        if not order:
            send_driver_message(driver_chat_id, "❌ Order not found.")
            return
            
        order.driver_id = driver.id
        order.status = 'accepted'
        driver.is_available = False
        db.session.commit()
        
        # Send confirmation
        message = f"✅ *Order Accepted*\n\n"
        message += f"📋 Order #{order_id} has been accepted!\n"
        message += f"🎯 Please proceed to ET-FOOD Kitchen to collect the order.\n\n"
        message += f"📍 Restaurant: ET-FOOD Kitchen\n"
        message += f"📞 Restaurant Phone: +251-911-123-456\n\n"
        message += f"🚚 Remember to share your live location for tracking."
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📍 Share Live Location",
                        "callback_data": f"driver_location_{order_id}"
                    }
                ],
                [
                    {
                        "text": "📞 Call Restaurant",
                        "callback_data": f"call_restaurant_{order_id}"
                    },
                    {
                        "text": "📞 Call Customer", 
                        "callback_data": f"call_customer_{order_id}"
                    }
                ]
            ]
        }
        
        send_driver_message(driver_chat_id, message, keyboard=keyboard)
        
        # Notify customer about acceptance
        from bot_minimal import notify_customer_status_change
        notify_customer_status_change(order_id, 'accepted')
        
    except Exception as e:
        logger.error(f"Error handling order acceptance: {e}")

def handle_order_rejection(driver_chat_id, order_id, message_id):
    """Handle order rejection by driver"""
    try:
        message = f"❌ *Order Rejected*\n\n"
        message += f"📋 Order #{order_id} has been rejected.\n"
        message += f"🔄 The order will be reassigned to another driver.\n\n"
        message += f"Thank you for your response!"
        
        send_driver_message(driver_chat_id, message)
        
        # TODO: Reassign order to another driver or delivery bot
        
    except Exception as e:
        logger.error(f"Error handling order rejection: {e}")

def request_driver_location_sharing(driver_chat_id, order_id):
    """Request driver to share live location"""
    try:
        message = f"📍 *Location Sharing Required*\n\n"
        message += f"Please share your live location so customers and admin can track the delivery progress.\n\n"
        message += f"🎯 This helps provide accurate delivery estimates and improves customer experience."
        
        keyboard = {
            "keyboard": [
                [
                    {
                        "text": "📍 Share Live Location",
                        "request_location": True
                    }
                ]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        send_driver_message(driver_chat_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error requesting location: {e}")

def answer_callback_query(callback_query_id, text):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/answerCallbackQuery"
    data = {
        'callback_query_id': callback_query_id,
        'text': text
    }
    
    try:
        requests.post(url, data=data)
    except Exception as e:
        logger.error(f"Error answering callback query: {e}")

def handle_driver_location_update(chat_id, location):
    """Handle driver location update"""
    try:
        from models import Driver
        from extensions import db
        
        driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
        if driver:
            driver.current_lat = location['latitude']
            driver.current_lng = location['longitude']
            driver.last_location_update = datetime.utcnow()
            db.session.commit()
            
            send_driver_message(chat_id, "📍 Location updated successfully! Admin can now track your delivery.\n\n⚠️ **Keep sharing your location regularly** to receive order assignments in your area.")
            
    except Exception as e:
        logger.error(f"Error updating driver location: {e}")

def init_driver_bot(flask_app):
    """Initialize the driver bot with Flask app context"""
    with flask_app.app_context():
        logger.info("Initializing Driver Telegram bot...")
        
        # Set up webhook
        setup_driver_webhook(flask_app)
        
        logger.info("Driver bot initialized successfully!")

def setup_driver_webhook(flask_app):
    """Set up webhook for the driver bot"""
    with flask_app.app_context():
        @flask_app.route('/driver-webhook', methods=['POST'])
        def driver_webhook():
            """Handle driver bot webhook"""
            try:
                update = request.get_json()
                
                if 'message' in update:
                    message = update['message']
                    chat_id = message['from']['id']
                    
                    if 'location' in message:
                        handle_driver_location_update(chat_id, message['location'])
                    elif 'text' in message:
                        handle_driver_text_message(chat_id, message['text'])
                        
                elif 'callback_query' in update:
                    handle_driver_callback(update['callback_query'])
                    
                return jsonify({'status': 'ok'})
                
            except Exception as e:
                logger.error(f"Error processing driver webhook: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Set webhook
        set_driver_webhook()

def handle_driver_text_message(chat_id, text):
    """Handle text messages from drivers"""
    if text == '/start':
        send_driver_welcome_message(chat_id)
    elif text == '/help':
        send_driver_help_message(chat_id)
    elif text == '/status':
        send_driver_status_message(chat_id)
    elif text == '/location':
        send_location_request(chat_id)
    elif text == '/orders':
        send_driver_orders(chat_id)
    elif text == '/toggle':
        toggle_driver_availability(chat_id)
    elif text == '/earnings':
        send_driver_earnings(chat_id)
    elif text == '/test':
        # Test command to verify bot is working
        send_driver_message(chat_id, "✅ Driver bot is working correctly!\n\nThis is a test message to verify the connection.")
    else:
        send_driver_message(chat_id, "🤖 I'm the ET-FOOD Driver Bot!\n\nI'll notify you about new delivery assignments. Use /help for more information.")

def send_driver_welcome_message(chat_id):
    """Send welcome message to driver with mandatory location sharing"""
    message = f"🚚 *Welcome to ET-FOOD Driver Bot!*\n\n"
    message += f"⚠️ **MANDATORY LOCATION SHARING REQUIRED**\n\n"
    message += f"To receive order assignments, you MUST:\n"
    message += f"✅ Share your current location\n"
    message += f"✅ Keep live location sharing ON\n"
    message += f"✅ Update location every 5 minutes\n\n"
    message += f"📍 **PLEASE SHARE YOUR LOCATION NOW** to activate your driver account.\n\n"
    message += f"Without location sharing, you won't receive any order assignments.\n\n"
    message += f"📋 What I can do:\n"
    message += f"• Notify you about new orders in your area\n"
    message += f"• Show order details and customer info\n"
    message += f"• Calculate distances and delivery routes\n"
    message += f"• Help you accept/reject orders\n"
    message += f"• Track your location for real-time monitoring\n\n"
    message += f"🎯 Click 'Share Location' below to get started!"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Share Location (REQUIRED)",
                    "callback_data": "request_location"
                }
            ],
            [
                {
                    "text": "🔄 Enable Live Location",
                    "callback_data": "enable_live_location"
                }
            ],
            [
                {
                    "text": "📱 Open Driver Panel",
                    "web_app": {"url": f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/driver-panel"}
                }
            ],
            [
                {
                    "text": "📞 Contact Support",
                    "callback_data": "contact_support"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_driver_status_message(chat_id):
    """Send driver status information"""
    try:
        from models import Driver, Order
        from extensions import db
        
        driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
        if not driver:
            send_driver_message(chat_id, "❌ You are not registered as a driver. Contact admin for registration.")
            return
        
        # Get active orders
        active_orders = Order.query.filter_by(driver_id=driver.id).filter(
            Order.status.in_(['out_for_delivery', 'preparing', 'confirmed'])
        ).all()
        
        message = f"📊 *Your Driver Status*\n\n"
        message += f"👤 Name: {driver.name}\n"
        message += f"🚗 Vehicle: {driver.vehicle_type.title()}\n"
        message += f"📞 Phone: {driver.phone_number}\n"
        message += f"✅ Status: {'Active' if driver.is_active else 'Inactive'}\n"
        message += f"🔄 Availability: {'Available' if driver.is_available else 'Busy'}\n"
        message += f"🎯 Approval: {'Approved' if driver.is_approved else 'Pending'}\n\n"
        message += f"📋 Active Orders: {len(active_orders)}\n"
        
        if active_orders:
            message += f"\n🚚 *Current Deliveries:*\n"
            for order in active_orders:
                message += f"• Order #{order.id} - {order.customer_name} ({order.status})\n"
        
        # Check location sharing status
        from datetime import datetime, timedelta
        message += f"\n📍 **Location Sharing Status:**\n"
        if driver.last_location_update:
            time_diff = datetime.utcnow() - driver.last_location_update
            if time_diff.total_seconds() < 600:  # Less than 10 minutes
                message += f"✅ Active (last update: {driver.last_location_update.strftime('%H:%M')})\n"
                message += f"🟢 **You can receive order assignments**\n"
            else:
                message += f"⚠️ Outdated (last update: {driver.last_location_update.strftime('%Y-%m-%d %H:%M')})\n"
                message += f"🔴 **You won't receive orders - please share location**\n"
        else:
            message += f"❌ No location shared\n"
            message += f"🔴 **You won't receive orders - please share location**\n"
        
        # Add location sharing buttons if location is outdated or missing
        keyboard = None
        if not driver.last_location_update or (datetime.utcnow() - driver.last_location_update).total_seconds() >= 600:
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📍 Share Location Now",
                            "callback_data": "request_location"
                        }
                    ],
                    [
                        {
                            "text": "🔄 Enable Live Location",
                            "callback_data": "enable_live_location"
                        }
                    ]
                ]
            }
        
        send_driver_message(chat_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error getting driver status: {e}")
        send_driver_message(chat_id, "❌ Error retrieving status. Please try again later.")

def send_driver_help_message(chat_id):
    """Send help message to driver"""
    message = """🚚 *Driver Bot Help*

Available commands:
• /start - Welcome message and setup
• /status - Check your driver status
• /location - Share your current location
• /orders - View your active orders
• /toggle - Toggle availability on/off
• /earnings - View your earnings summary
• /help - Show this help message

I'll automatically notify you about new delivery assignments. When you get an order notification, you can:
• Use the WebApp to view full order details
• Quick accept or reject using buttons
• Share your location for tracking

Stay online and ready for deliveries! 🚀"""
    
    send_driver_message(chat_id, message)

def send_driver_orders(chat_id):
    """Send driver's current orders"""
    try:
        from models import Driver, Order
        from main import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if not driver:
                send_driver_message(chat_id, "❌ Driver profile not found. Please contact admin.")
                return
            
            active_orders = Order.query.filter_by(driver_id=driver.id).filter(
                Order.status.in_(['confirmed', 'preparing', 'out_for_delivery'])
            ).all()
            
            if not active_orders:
                send_driver_message(chat_id, "📋 No active orders at the moment.\n\nYou'll be notified when new orders are available!")
                return
            
            message = f"📋 *Your Active Orders ({len(active_orders)})*\n\n"
            
            for order in active_orders:
                status_emoji = {
                    'confirmed': '✅',
                    'preparing': '👨‍🍳',
                    'out_for_delivery': '🚚'
                }.get(order.status, '📦')
                
                message += f"{status_emoji} *Order #{order.id}*\n"
                message += f"👤 {order.customer_name}\n"
                message += f"📞 {order.customer_phone}\n"
                message += f"📍 {order.customer_address}\n"
                message += f"💰 {order.total_amount:.2f} ETB\n"
                message += f"📦 Status: {order.status.replace('_', ' ').title()}\n"
                message += "─────────────────\n"
            
            # Add WebApp button for full order management
            webapp_url = f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/driver-panel?driver_id={driver.id}"
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📱 Open Driver Panel",
                            "web_app": {"url": webapp_url}
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error getting driver orders: {e}")
        send_driver_message(chat_id, "❌ Error retrieving orders. Please try again later.")

def toggle_driver_availability(chat_id):
    """Toggle driver availability status"""
    try:
        from models import Driver
        from extensions import db
        from main import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if not driver:
                send_driver_message(chat_id, "❌ Driver profile not found. Please contact admin.")
                return
            
            # Toggle availability
            driver.is_available = not driver.is_available
            db.session.commit()
            
            status = "🟢 AVAILABLE" if driver.is_available else "🔴 UNAVAILABLE"
            action = "receive" if driver.is_available else "NOT receive"
            
            message = f"✅ Status updated!\n\n📊 *Current Status:* {status}\n\n"
            message += f"You will {action} new order notifications."
            
            if driver.is_available:
                message += "\n\n📍 *Important:* Make sure to share your location regularly for accurate order assignments!"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📍 Share Location Now",
                                "callback_data": "driver_location_share"
                            }
                        ]
                    ]
                }
                send_driver_message(chat_id, message, keyboard=keyboard)
            else:
                send_driver_message(chat_id, message)
                
    except Exception as e:
        logger.error(f"Error toggling driver availability: {e}")
        send_driver_message(chat_id, "❌ Error updating status. Please try again later.")

def send_driver_earnings(chat_id):
    """Send driver earnings summary"""
    try:
        from models import Driver, Order
        from main import app
        from datetime import datetime, timedelta
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if not driver:
                send_driver_message(chat_id, "❌ Driver profile not found. Please contact admin.")
                return
            
            # Calculate earnings for different periods
            today = datetime.utcnow().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Get completed orders
            completed_orders = Order.query.filter_by(
                driver_id=driver.id,
                status='delivered'
            ).all()
            
            # Calculate earnings (assuming 10% commission per order)
            today_orders = [o for o in completed_orders if o.created_at.date() == today]
            week_orders = [o for o in completed_orders if o.created_at.date() >= week_ago]
            month_orders = [o for o in completed_orders if o.created_at.date() >= month_ago]
            
            today_earnings = sum(o.total_amount * 0.1 for o in today_orders)
            week_earnings = sum(o.total_amount * 0.1 for o in week_orders)
            month_earnings = sum(o.total_amount * 0.1 for o in month_orders)
            total_earnings = sum(o.total_amount * 0.1 for o in completed_orders)
            
            message = f"💰 *Earnings Summary*\n\n"
            message += f"📅 *Today:* {today_earnings:.2f} ETB ({len(today_orders)} orders)\n"
            message += f"📈 *This Week:* {week_earnings:.2f} ETB ({len(week_orders)} orders)\n"
            message += f"📊 *This Month:* {month_earnings:.2f} ETB ({len(month_orders)} orders)\n"
            message += f"🎯 *Total:* {total_earnings:.2f} ETB ({len(completed_orders)} orders)\n\n"
            message += f"💼 *Average per order:* {(total_earnings/len(completed_orders)):.2f} ETB" if completed_orders else "💼 *Average per order:* 0 ETB"
            
            # Add performance stats
            if completed_orders:
                message += f"\n\n📊 *Performance Stats:*\n"
                message += f"✅ Completed: {len(completed_orders)} orders\n"
                message += f"🚚 Vehicle: {driver.vehicle_type.title()}\n"
                message += f"⭐ Status: {'Available' if driver.is_available else 'Unavailable'}"
            
            send_driver_message(chat_id, message)
            
    except Exception as e:
        logger.error(f"Error getting driver earnings: {e}")
        send_driver_message(chat_id, "❌ Error retrieving earnings. Please try again later.")
        send_driver_message(chat_id, "❌ Error retrieving status information.")

def send_driver_help_message(chat_id):
    """Send help message to driver"""
    message = f"🆘 *Driver Bot Help*\n\n"
    message += f"*Available Commands:*\n"
    message += f"• /start - Welcome message\n"
    message += f"• /help - This help message\n\n"
    message += f"*How it works:*\n"
    message += f"1️⃣ You'll receive notifications for new orders\n"
    message += f"2️⃣ Open the Driver Panel to see full details\n"
    message += f"3️⃣ Accept or reject the order\n"
    message += f"4️⃣ Share your location for tracking\n"
    message += f"5️⃣ Complete the delivery\n\n"
    message += f"*Need Support?*\n"
    message += f"📞 Call: +251-911-123-456\n"
    message += f"📧 Email: support@et-food.com"
    
    send_driver_message(chat_id, message)

def set_driver_webhook():
    """Set webhook for driver bot"""
    webhook_url = f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/driver-webhook"
    url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/setWebhook"
    
    data = {
        'url': webhook_url,
        'allowed_updates': ['message', 'callback_query']
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            logger.info(f"Driver bot webhook set successfully: {webhook_url}")
        else:
            logger.error(f"Failed to set driver webhook: {response.text}")
    except Exception as e:
        logger.error(f"Error setting driver webhook: {e}")

# Integration function for main system
def notify_driver_assignment_via_driver_bot(driver_telegram_id, order_data):
    """Main function to notify driver via driver bot"""
    if DRIVER_BOT_TOKEN and driver_telegram_id:
        logger.info(f"Sending driver notification to Telegram ID: {driver_telegram_id} for order {order_data.get('id')}")
        notify_driver_order_assignment(driver_telegram_id, order_data)
    else:
        logger.warning(f"Driver bot notification failed - Token: {bool(DRIVER_BOT_TOKEN)}, Telegram ID: {driver_telegram_id}")

def handle_pickup_complete(chat_id, order_id):
    """Handle pickup completion notification"""
    try:
        from models import Order
        from extensions import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                send_driver_message(chat_id, "❌ Order not found")
                return
            
            # Update order status
            order.status = 'out_for_delivery'
            db.session.commit()
            
            # Send confirmation to driver
            message = f"✅ *Pickup Confirmed!*\n\n"
            message += f"📋 Order #{order_id}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"🏠 Address: {order.customer_address}\n\n"
            message += f"🚚 Status updated to 'Out for Delivery'\n"
            message += f"📍 Keep sharing your location for customer tracking"
            
            delivery_keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📍 Share Location",
                            "callback_data": f"share_location_{order_id}"
                        }
                    ],
                    [
                        {
                            "text": "✅ Delivered",
                            "callback_data": f"delivery_complete_{order_id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, delivery_keyboard)
            
            # Notify customer
            from bot_minimal import send_message
            customer_message = f"🚚 *Your order is on the way!*\n\n"
            customer_message += f"📋 Order #{order_id}\n"
            customer_message += f"✅ Status: Out for Delivery\n"
            customer_message += f"⏱️ Estimated delivery: 15-25 minutes\n\n"
            customer_message += f"Your driver is heading to your location now!"
            
            send_message(order.telegram_user_id, customer_message)
            
    except Exception as e:
        logger.error(f"Error handling pickup complete: {e}")
        send_driver_message(chat_id, "❌ Error updating pickup status")