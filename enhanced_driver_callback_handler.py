"""
Enhanced Driver Callback Handler
Handles all driver bot callback queries with smart location tracking
"""

import os
import logging
import requests
import json
from datetime import datetime, timedelta
from enhanced_driver_location_system import driver_location_tracker

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Driver Bot Configuration
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')

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
            return True
        else:
            logger.error(f"Failed to send message: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def handle_enhanced_driver_callback(callback_query):
    """Handle enhanced driver callback queries with smart location tracking"""
    try:
        chat_id = callback_query['message']['chat']['id']
        callback_data = callback_query['data']
        
        # Answer callback query first
        answer_callback_query(callback_query['id'], "Processing...")
        
        if callback_data == "start_live_location":
            handle_start_live_location(chat_id)
        elif callback_data == "location_help":
            handle_location_help(chat_id)
        elif callback_data == "location_status":
            handle_location_status(chat_id)
        elif callback_data == "driver_status":
            handle_driver_status(chat_id)
        elif callback_data == "driver_orders":
            handle_driver_orders(chat_id)
        elif callback_data == "toggle_availability":
            handle_toggle_availability(chat_id)
        elif callback_data == "driver_earnings":
            handle_driver_earnings(chat_id)
        elif callback_data == "ready_for_orders":
            handle_ready_for_orders(chat_id)
        elif callback_data.startswith("accept_order_") or callback_data.startswith("driver_accept_"):
            if callback_data.startswith("accept_order_"):
                order_id = callback_data.replace("accept_order_", "")
            else:
                order_id = callback_data.replace("driver_accept_", "")
            handle_order_acceptance(chat_id, order_id)
        elif callback_data.startswith("decline_order_") or callback_data.startswith("driver_reject_"):
            if callback_data.startswith("decline_order_"):
                order_id = callback_data.replace("decline_order_", "")
            else:
                order_id = callback_data.replace("driver_reject_", "")
            handle_order_decline(chat_id, order_id)
        elif callback_data.startswith("complete_order_"):
            order_id = callback_data.replace("complete_order_", "")
            handle_order_completion(chat_id, order_id)
        elif callback_data.startswith("call_customer_"):
            order_id = callback_data.replace("call_customer_", "")
            handle_call_customer(chat_id, order_id)
        elif callback_data.startswith("call_restaurant_"):
            order_id = callback_data.replace("call_restaurant_", "")
            handle_call_restaurant(chat_id, order_id)
        elif callback_data.startswith("pickup_complete_"):
            order_id = callback_data.replace("pickup_complete_", "")
            handle_pickup_complete(chat_id, order_id)
        elif callback_data.startswith("delivery_complete_"):
            order_id = callback_data.replace("delivery_complete_", "")
            handle_delivery_complete(chat_id, order_id)
        else:
            # Unknown callback - log it and send helpful message
            logger.warning(f"Unknown callback data received: {callback_data}")
            send_driver_message(chat_id, f"⚠️ Unknown action. Please try again or use the menu buttons.")
            # Handle other callback data
            handle_generic_callback(chat_id, callback_data)
            
    except Exception as e:
        logger.error(f"Error handling enhanced driver callback: {e}")
        
def handle_start_live_location(chat_id):
    """Handle start live location callback"""
    success = driver_location_tracker.request_initial_location_sharing(chat_id)
    if not success:
        # Fallback message
        message = "📍 **Share Live Location**\n\n"
        message += "To start receiving orders automatically:\n\n"
        message += "1️⃣ Tap the 📎 attachment button\n"
        message += "2️⃣ Select 'Location'\n"
        message += "3️⃣ Choose 'Share Live Location'\n"
        message += "4️⃣ Set duration: 8 hours\n"
        message += "5️⃣ Tap 'Send'\n\n"
        message += "✅ Once active, you'll receive orders automatically!"
        
        send_driver_message(chat_id, message)
        
def handle_location_help(chat_id):
    """Handle location help callback"""
    message = "📍 **How to Share Live Location**\n\n"
    message += "**Step-by-step guide:**\n\n"
    message += "📱 **On Mobile:**\n"
    message += "1️⃣ Open this chat\n"
    message += "2️⃣ Tap the 📎 attachment button\n"
    message += "3️⃣ Select 'Location'\n"
    message += "4️⃣ Choose 'Share Live Location'\n"
    message += "5️⃣ Set duration: 8 hours (recommended)\n"
    message += "6️⃣ Tap 'Send'\n\n"
    message += "🖥️ **On Desktop:**\n"
    message += "1️⃣ Click the 📎 attachment button\n"
    message += "2️⃣ Select 'Location'\n"
    message += "3️⃣ Allow location access\n"
    message += "4️⃣ Choose 'Share Live Location'\n"
    message += "5️⃣ Set duration and send\n\n"
    message += "✅ **Benefits:**\n"
    message += "• Automatic order assignments\n"
    message += "• No need to share location repeatedly\n"
    message += "• Real-time customer tracking\n"
    message += "• Higher priority for nearby orders\n\n"
    message += "❗ **Important**: Keep live location active during your shift!"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🔄 Try Again",
                    "callback_data": "start_live_location"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)
    
def handle_location_status(chat_id):
    """Handle location status callback"""
    is_sharing_live = driver_location_tracker.is_driver_sharing_live_location(chat_id)
    
    if is_sharing_live:
        session = driver_location_tracker.live_location_sessions.get(chat_id, {})
        started_at = session.get('started_at', datetime.utcnow())
        last_update = session.get('last_update', datetime.utcnow())
        location_count = session.get('location_count', 0)
        
        duration = datetime.utcnow() - started_at
        last_update_mins = int((datetime.utcnow() - last_update).total_seconds() / 60)
        
        message = f"📍 **Live Location Status**\n\n"
        message += f"🟢 **Status**: ACTIVE\n"
        message += f"⏱️ **Duration**: {int(duration.total_seconds() / 3600)}h {int((duration.total_seconds() % 3600) / 60)}m\n"
        message += f"🔄 **Updates**: {location_count} received\n"
        message += f"📡 **Last update**: {last_update_mins} minutes ago\n\n"
        message += f"✅ **Features active:**\n"
        message += f"• Automatic order assignments\n"
        message += f"• Real-time customer tracking\n"
        message += f"• Priority order matching\n"
        message += f"• Distance-based assignments\n\n"
        message += f"💡 **System working perfectly!**"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🔄 Refresh Status",
                        "callback_data": "location_status"
                    }
                ]
            ]
        }
    else:
        message = f"📍 **Live Location Status**\n\n"
        message += f"🔴 **Status**: INACTIVE\n"
        message += f"❌ **Order assignments**: DISABLED\n\n"
        message += f"⚠️ **Action required:**\n"
        message += f"You need to share your live location to receive orders automatically.\n\n"
        message += f"💡 **Benefits of live location:**\n"
        message += f"• Instant order notifications\n"
        message += f"• Automatic nearby order matching\n"
        message += f"• Real-time tracking for customers\n"
        message += f"• Higher earnings potential\n\n"
        message += f"👇 **Set up live location now:**"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📍 Start Live Location",
                        "callback_data": "start_live_location"
                    }
                ],
                [
                    {
                        "text": "ℹ️ How to Share",
                        "callback_data": "location_help"
                    }
                ]
            ]
        }
    
    send_driver_message(chat_id, message, keyboard=keyboard)
    
def handle_driver_status(chat_id):
    """Handle driver status callback"""
    try:
        from models import Driver
        from app import db
        from main import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if not driver:
                send_driver_message(chat_id, "❌ Driver profile not found. Please contact admin.")
                return
                
            is_sharing_live = driver_location_tracker.is_driver_sharing_live_location(chat_id)
            
            message = f"📊 **Driver Status Dashboard**\n\n"
            message += f"👤 **Driver**: {driver.name}\n"
            message += f"📞 **Phone**: {driver.phone_number}\n"
            message += f"🚗 **Vehicle**: {driver.vehicle_type}\n\n"
            message += f"🔄 **Current Status:**\n"
            message += f"• Active: {'✅ Yes' if driver.is_active else '❌ No'}\n"
            message += f"• Available: {'✅ Yes' if driver.is_available else '❌ No'}\n"
            message += f"• Live Location: {'🟢 Active' if is_sharing_live else '🔴 Inactive'}\n\n"
            
            if driver.last_location_update:
                time_diff = datetime.utcnow() - driver.last_location_update
                message += f"📍 **Last Location Update**: {int(time_diff.total_seconds() / 60)} minutes ago\n\n"
            
            if driver.is_active and driver.is_available and is_sharing_live:
                message += f"🎉 **Ready to receive orders!**\n"
                message += f"✅ All systems active and operational"
            else:
                message += f"⚠️ **Action needed to receive orders:**\n"
                if not driver.is_active:
                    message += f"• Enable driver status\n"
                if not driver.is_available:
                    message += f"• Set availability to 'Available'\n"
                if not is_sharing_live:
                    message += f"• Share live location\n"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🎯 Toggle Availability",
                            "callback_data": "toggle_availability"
                        }
                    ],
                    [
                        {
                            "text": "📍 Location Status",
                            "callback_data": "location_status"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error handling driver status: {e}")
        send_driver_message(chat_id, "❌ Error loading status. Please try again.")

def handle_driver_orders(chat_id):
    """Handle driver orders callback"""
    try:
        from models import Order, Driver
        from app import db
        from main import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if not driver:
                send_driver_message(chat_id, "❌ Driver profile not found.")
                return
                
            # Get active orders for this driver
            active_orders = Order.query.filter_by(driver_id=driver.id).filter(
                Order.status.in_(['confirmed', 'preparing', 'ready', 'out_for_delivery'])
            ).order_by(Order.created_at.desc()).all()
            
            if not active_orders:
                message = f"📦 **Your Orders**\n\n"
                message += f"🎯 **No active orders**\n\n"
                message += f"📍 Keep your live location active to receive nearby orders automatically!\n\n"
                
                is_sharing_live = driver_location_tracker.is_driver_sharing_live_location(chat_id)
                if is_sharing_live:
                    message += f"✅ **Live location active** - You'll receive orders soon!"
                else:
                    message += f"❌ **Live location inactive** - Enable it to receive orders!"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📍 Check Location Status",
                                "callback_data": "location_status"
                            }
                        ],
                        [
                            {
                                "text": "🔄 Refresh Orders",
                                "callback_data": "driver_orders"
                            }
                        ]
                    ]
                }
            else:
                message = f"📦 **Your Active Orders**\n\n"
                
                for order in active_orders:
                    status_emoji = {
                        'confirmed': '✅',
                        'preparing': '👨‍🍳',
                        'ready': '🍽️',
                        'out_for_delivery': '🚚'
                    }.get(order.status, '📦')
                    
                    message += f"{status_emoji} **Order #{order.id}**\n"
                    message += f"👤 {order.customer_name}\n"
                    message += f"💰 {order.total_amount} ETB\n"
                    message += f"📍 {order.customer_address}\n"
                    message += f"🔄 Status: {order.status.title()}\n\n"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "🔄 Refresh Orders",
                                "callback_data": "driver_orders"
                            }
                        ]
                    ]
                }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error handling driver orders: {e}")
        send_driver_message(chat_id, "❌ Error loading orders. Please try again.")

def handle_toggle_availability(chat_id):
    """Handle toggle availability callback"""
    try:
        from models import Driver
        from app import db
        from main import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if not driver:
                send_driver_message(chat_id, "❌ Driver profile not found.")
                return
                
            # Toggle availability
            driver.is_available = not driver.is_available
            # Also activate driver when they become available
            if driver.is_available:
                driver.is_active = True
            db.session.commit()
            
            status = "Available" if driver.is_available else "Busy"
            emoji = "✅" if driver.is_available else "❌"
            
            message = f"🎯 **Availability Updated**\n\n"
            message += f"{emoji} **Status**: {status}\n\n"
            
            if driver.is_available:
                message += f"🟢 **You're now available for orders!**\n"
                message += f"📍 Make sure your live location is active to receive nearby orders automatically."
                
                # Check if driver is sharing live location
                is_sharing_live = driver_location_tracker.is_driver_sharing_live_location(chat_id)
                if is_sharing_live:
                    message += f"\n\n✅ **Live location active** - Ready to receive orders!"
                    # Check for pending orders
                    driver_location_tracker.check_for_pending_orders(chat_id)
                else:
                    message += f"\n\n❌ **Live location inactive** - Enable it to receive orders!"
            else:
                message += f"🔴 **You're now busy** - No new orders will be assigned."
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": f"🎯 Set to {'Busy' if driver.is_available else 'Available'}",
                            "callback_data": "toggle_availability"
                        }
                    ],
                    [
                        {
                            "text": "📍 Location Status",
                            "callback_data": "location_status"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error toggling availability: {e}")
        send_driver_message(chat_id, "❌ Error updating availability. Please try again.")

def handle_driver_earnings(chat_id):
    """Handle driver earnings callback"""
    try:
        from models import Order, Driver
        from app import db
        from main import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if not driver:
                send_driver_message(chat_id, "❌ Driver profile not found.")
                return
                
            # Calculate earnings
            completed_orders = Order.query.filter_by(
                driver_id=driver.id,
                status='delivered'
            ).all()
            
            total_earnings = sum(float(order.total_amount) for order in completed_orders)
            total_orders = len(completed_orders)
            
            # Today's earnings
            today = datetime.utcnow().date()
            today_orders = [order for order in completed_orders if order.created_at.date() == today]
            today_earnings = sum(float(order.total_amount) for order in today_orders)
            today_count = len(today_orders)
            
            # This week's earnings
            week_start = datetime.utcnow() - timedelta(days=7)
            week_orders = [order for order in completed_orders if order.created_at >= week_start]
            week_earnings = sum(float(order.total_amount) for order in week_orders)
            week_count = len(week_orders)
            
            message = f"💰 **Earnings Summary**\n\n"
            message += f"📊 **Today ({today.strftime('%Y-%m-%d')})**\n"
            message += f"• Orders: {today_count}\n"
            message += f"• Earnings: {today_earnings:.2f} ETB\n\n"
            message += f"📈 **This Week**\n"
            message += f"• Orders: {week_count}\n"
            message += f"• Earnings: {week_earnings:.2f} ETB\n\n"
            message += f"🎯 **Total**\n"
            message += f"• Orders: {total_orders}\n"
            message += f"• Earnings: {total_earnings:.2f} ETB\n\n"
            
            if total_orders > 0:
                avg_per_order = total_earnings / total_orders
                message += f"📊 **Average per order**: {avg_per_order:.2f} ETB"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔄 Refresh Earnings",
                            "callback_data": "driver_earnings"
                        }
                    ],
                    [
                        {
                            "text": "📦 View Orders",
                            "callback_data": "driver_orders"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error handling driver earnings: {e}")
        send_driver_message(chat_id, "❌ Error loading earnings. Please try again.")

def handle_ready_for_orders(chat_id):
    """Handle ready for orders callback"""
    # Check for pending orders
    driver_location_tracker.check_for_pending_orders(chat_id)
    
    message = f"🎯 **Ready for Orders!**\n\n"
    message += f"✅ Checking for nearby orders...\n"
    message += f"📍 Your live location is being used to find the best matches\n\n"
    message += f"💡 **You'll receive notifications automatically** when orders are available in your area!\n\n"
    message += f"🔄 Keep your live location active for continuous order assignments."
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Location Status",
                    "callback_data": "location_status"
                }
            ],
            [
                {
                    "text": "📊 My Status",
                    "callback_data": "driver_status"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def handle_order_acceptance(chat_id, order_id):
    """Handle order acceptance"""
    try:
        from models import Order, Driver
        from app import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                send_driver_message(chat_id, "❌ Order or driver not found.")
                return
                
            if order.driver_id:
                send_driver_message(chat_id, f"❌ Order #{order_id} has already been assigned to another driver.")
                return
                
            # Assign order to driver
            order.driver_id = driver.id
            order.status = 'out_for_delivery'
            order.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Send confirmation to driver
            message = f"✅ **Order Accepted!**\n\n"
            message += f"📦 **Order #{order_id}**\n"
            message += f"👤 **Customer**: {order.customer_name}\n"
            message += f"📞 **Phone**: {order.customer_phone}\n"
            message += f"📍 **Address**: {order.customer_address}\n"
            message += f"💰 **Amount**: {order.total_amount} ETB\n"
            message += f"💳 **Payment**: {order.payment_method}\n\n"
            message += f"🎯 **Next Steps:**\n"
            message += f"1. Navigate to customer location\n"
            message += f"2. Call customer if needed\n"
            message += f"3. Complete delivery\n"
            message += f"4. Mark as delivered\n\n"
            message += f"📱 **Quick Actions:**"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": f"📞 Call {order.customer_name}",
                            "callback_data": f"call_customer_{order_id}"
                        }
                    ],
                    [
                        {
                            "text": "🗺️ Navigate to Customer",
                            "url": f"https://maps.google.com/maps?q={order.location_lat},{order.location_lng}"
                        }
                    ],
                    [
                        {
                            "text": "✅ Pickup Complete",
                            "callback_data": f"pickup_complete_{order_id}"
                        },
                        {
                            "text": "✅ Mark as Delivered",
                            "callback_data": f"complete_order_{order_id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
            # Notify customer about driver assignment
            notify_customer_about_driver(order_id, driver)
            
            # Notify admin about assignment
            notify_admin_about_assignment(order_id, driver)
            
    except Exception as e:
        logger.error(f"Error handling order acceptance: {e}")
        send_driver_message(chat_id, "❌ Error accepting order. Please try again.")

def handle_order_decline(chat_id, order_id):
    """Handle order decline"""
    message = f"❌ **Order Declined**\n\n"
    message += f"📦 Order #{order_id} has been declined.\n"
    message += f"🔄 The system will look for other available drivers.\n\n"
    message += f"💡 **Stay ready** - More orders will be available soon!"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🎯 Ready for Orders",
                    "callback_data": "ready_for_orders"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def handle_order_completion(chat_id, order_id):
    """Handle order completion"""
    try:
        from models import Order, Driver
        from app import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                send_driver_message(chat_id, "❌ Order or driver not found.")
                return
                
            if order.driver_id != driver.id:
                send_driver_message(chat_id, "❌ This order is not assigned to you.")
                return
                
            # Mark order as delivered
            order.status = 'delivered'
            order.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Handle delivery completion through enhanced system
            driver_location_tracker.handle_delivery_completion(chat_id, order_id)
            
            # Notify customer about delivery completion
            notify_customer_delivery_completion(order_id)
            
            # Notify admin about completion
            notify_admin_delivery_completion(order_id, driver)
            
    except Exception as e:
        logger.error(f"Error handling order completion: {e}")
        send_driver_message(chat_id, "❌ Error completing order. Please try again.")

def handle_generic_callback(chat_id, callback_data):
    """Handle other callback queries"""
    if callback_data == "contact_support":
        message = "📞 **Contact Support**\n\n"
        message += "Need help? Contact our support team:\n\n"
        message += "📱 **Phone**: +251-XXX-XXXX\n"
        message += "💬 **Admin**: Available 24/7\n"
        message += "🕐 **Response time**: Usually within 30 minutes\n\n"
        message += "🎯 **Common issues:**\n"
        message += "• Location sharing problems\n"
        message += "• Order assignment issues\n"
        message += "• Account or payment questions\n"
        message += "• Technical support"
        
        send_driver_message(chat_id, message)
    else:
        send_driver_message(chat_id, "❓ Unknown command. Please try again or contact support.")

def answer_callback_query(callback_query_id, text):
    """Answer callback query"""
    url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/answerCallbackQuery"
    data = {
        'callback_query_id': callback_query_id,
        'text': text
    }
    
    try:
        response = requests.post(url, data=data)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Error answering callback query: {e}")
        return False

def notify_customer_about_driver(order_id, driver):
    """Notify customer about driver assignment"""
    try:
        from bot_minimal import send_message_to_admin
        from models import Order
        from app import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if order:
                message = f"🚚 **Driver Assigned!**\n\n"
                message += f"📦 **Order #{order_id}**\n"
                message += f"👤 **Driver**: {driver.name}\n"
                message += f"📞 **Phone**: {driver.phone_number}\n"
                message += f"🚗 **Vehicle**: {driver.vehicle_type}\n\n"
                message += f"📍 **Status**: Driver is on the way to deliver your order!\n"
                message += f"⏰ **Estimated time**: 15-30 minutes\n\n"
                message += f"💡 **You can track the driver's location in real-time**"
                
                # Send to customer
                send_message_to_admin(order.telegram_user_id, message)
                
    except Exception as e:
        logger.error(f"Error notifying customer about driver: {e}")

def notify_admin_about_assignment(order_id, driver):
    """Notify admin about driver assignment"""
    try:
        from bot_minimal import send_message_to_admin
        
        message = f"✅ **Order Assigned**\n\n"
        message += f"📦 **Order #{order_id}**\n"
        message += f"👤 **Driver**: {driver.name}\n"
        message += f"📞 **Phone**: {driver.phone_number}\n"
        message += f"🚗 **Vehicle**: {driver.vehicle_type}\n\n"
        message += f"🎯 **Status**: Driver accepted the order and is on delivery route"
        
        # Send to admin (adjust admin telegram ID as needed)
        send_message_to_admin(383870191, message)
        
    except Exception as e:
        logger.error(f"Error notifying admin about assignment: {e}")

def notify_customer_delivery_completion(order_id):
    """Notify customer about delivery completion"""
    try:
        from bot_minimal import send_message_to_admin
        from models import Order
        from app import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if order:
                message = f"✅ **Order Delivered!**\n\n"
                message += f"📦 **Order #{order_id}** has been delivered successfully!\n"
                message += f"💰 **Amount**: {order.total_amount} ETB\n"
                message += f"📍 **Address**: {order.customer_address}\n\n"
                message += f"🌟 **Rate your experience:**\n"
                message += f"How was your delivery experience?\n\n"
                message += f"Thank you for choosing ET-FOOD!"
                
                # Send to customer
                send_message_to_admin(order.telegram_user_id, message)
                
    except Exception as e:
        logger.error(f"Error notifying customer about delivery completion: {e}")

def notify_admin_delivery_completion(order_id, driver):
    """Notify admin about delivery completion"""
    try:
        from bot_minimal import send_message_to_admin
        
        message = f"✅ **Delivery Completed**\n\n"
        message += f"📦 **Order #{order_id}** delivered successfully\n"
        message += f"👤 **Driver**: {driver.name}\n"
        message += f"📞 **Phone**: {driver.phone_number}\n"
        message += f"⏰ **Completed**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        message += f"🎯 **Driver is now available for new orders**"
        
        # Send to admin
        send_message_to_admin(383870191, message)
        
    except Exception as e:
        logger.error(f"Error notifying admin about delivery completion: {e}")

def notify_driver_about_orders(driver_telegram_id, order_id):
    """Notify driver about new order assignment"""
    try:
        from models import Order
        from app import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                return
                
            message = f"🔔 **New Order Available!**\n\n"
            message += f"📦 **Order #{order_id}**\n"
            message += f"👤 **Customer**: {order.customer_name}\n"
            message += f"📍 **Address**: {order.customer_address}\n"
            message += f"💰 **Amount**: {order.total_amount} ETB\n"
            message += f"💳 **Payment**: {order.payment_method}\n\n"
            message += f"🎯 **Quick Decision Required**\n"
            message += f"⏰ **30 seconds** to accept or decline\n\n"
            message += f"📍 **Distance**: Calculating from your location..."
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Accept Order",
                            "callback_data": f"accept_order_{order_id}"
                        },
                        {
                            "text": "❌ Decline",
                            "callback_data": f"decline_order_{order_id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver_telegram_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error notifying driver about orders: {e}")

def handle_call_customer(chat_id, order_id):
    """Handle call customer callback"""
    try:
        from models import Order
        from app import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if order:
                message = f"📞 **Customer Contact Information**\n\n"
                message += f"👤 **Name**: {order.customer_name}\n"
                message += f"📱 **Phone**: `{order.customer_phone}`\n"
                message += f"📍 **Address**: {order.customer_address}\n\n"
                message += f"💡 **Instructions**:\n"
                message += f"• Long press the phone number to copy\n"
                message += f"• Use your phone's dialer to call\n"
                message += f"• Contact customer for delivery coordination"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "🗺️ Navigate to Customer",
                                "url": f"https://maps.google.com/maps?q={order.location_lat},{order.location_lng}" if order.location_lat else "https://maps.google.com"
                            }
                        ],
                        [
                            {
                                "text": "✅ Pickup Complete",
                                "callback_data": f"pickup_complete_{order_id}"
                            },
                            {
                                "text": "✅ Mark as Delivered",
                                "callback_data": f"delivery_complete_{order_id}"
                            }
                        ]
                    ]
                }
                
                send_driver_message(chat_id, message, keyboard=keyboard)
            else:
                send_driver_message(chat_id, "❌ Order not found.")
    except Exception as e:
        logger.error(f"Error handling call customer: {e}")
        send_driver_message(chat_id, "❌ Error retrieving customer contact.")

def handle_call_restaurant(chat_id, order_id):
    """Handle call restaurant callback"""
    message = f"📞 **Restaurant Contact**\n\n"
    message += f"🏪 **ET-FOOD Kitchen**\n"
    message += f"📱 **Phone**: +251-911-123-456\n"
    message += f"📍 **Address**: Bole Road, Addis Ababa\n\n"
    message += f"💡 **Tip**: Call to coordinate pickup time"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📞 Call Restaurant",
                    "url": "tel:+251911123456"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def handle_pickup_complete(chat_id, order_id):
    """Handle pickup completion"""
    try:
        from models import Order, Driver
        from app import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                send_driver_message(chat_id, "❌ Order or driver not found.")
                return
                
            # Update order status
            order.status = 'out_for_delivery'
            order.updated_at = datetime.utcnow()
            db.session.commit()
            
            message = f"✅ **Pickup Confirmed**\n\n"
            message += f"📦 **Order #{order_id}** picked up successfully\n"
            message += f"🎯 **Status**: On the way to customer\n\n"
            message += f"📍 **Next**: Navigate to customer address\n"
            message += f"📞 **Contact customer** if needed"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order_id}"
                        },
                        {
                            "text": "🗺️ Navigate",
                            "url": f"https://maps.google.com/maps?q={order.location_lat},{order.location_lng}" if order.location_lat else "https://maps.google.com"
                        }
                    ],
                    [
                        {
                            "text": "✅ Mark as Delivered",
                            "callback_data": f"delivery_complete_{order_id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error handling pickup complete: {e}")
        send_driver_message(chat_id, "❌ Error updating pickup status.")

def handle_delivery_complete(chat_id, order_id):
    """Handle delivery completion"""
    try:
        from models import Order, Driver
        from app import db
        from main import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                send_driver_message(chat_id, "❌ Order or driver not found.")
                return
                
            # Mark order as delivered
            order.status = 'delivered'
            order.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Set driver as available
            driver.is_available = True
            db.session.commit()
            
            message = f"🎉 **Delivery Completed!**\n\n"
            message += f"📦 **Order #{order_id}** delivered successfully\n"
            message += f"👤 **Customer**: {order.customer_name}\n"
            message += f"💰 **Amount**: {order.total_amount} ETB\n\n"
            message += f"✅ **You are now available** for new orders\n"
            message += f"🎯 **Great job!** Keep up the excellent work."
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🎯 Ready for Orders",
                            "callback_data": "ready_for_orders"
                        },
                        {
                            "text": "💰 View Earnings",
                            "callback_data": "driver_earnings"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
            # Notify customer about delivery completion
            notify_customer_delivery_completion(order_id)
            
            # Notify admin about completion
            notify_admin_delivery_completion(order_id, driver)
            
    except Exception as e:
        logger.error(f"Error handling delivery complete: {e}")
        send_driver_message(chat_id, "❌ Error completing delivery.")