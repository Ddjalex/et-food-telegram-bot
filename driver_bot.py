"""
Enhanced Driver Bot - BeU Delivery Style
Handles live location sharing, order assignments, and automated driver dispatch
"""

import os
import logging
import requests
import json
import threading
import time
from datetime import datetime, timedelta
from flask import request, jsonify
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Driver Bot Configuration
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')

from url_utils import construct_webhook_url

DRIVER_WEBHOOK_URL = construct_webhook_url('driver-webhook')

# Order timeout tracking
pending_orders = {}
order_timers = {}

# Global variable to prevent duplicate initialization
_driver_bot_initialized = False

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
            response_data = response.json()
            if response_data.get('error_code') == 400 and 'chat not found' in response_data.get('description', ''):
                logger.warning(f"Driver {chat_id} has not started the driver bot yet. They need to start @Food_Driver_Bot first.")
                return False
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def send_location_request(driver_telegram_id):
    """Request driver to share their current location"""
    message = "📍 *Location Update Required*\n\n"
    message += "Please share your current location for order assignments.\n"
    message += "We need your live location to find you nearby delivery requests.\n\n"
    message += "👆 Use the button below to share your location:"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Share Live Location",
                    "callback_data": "share_live_location"
                }
            ],
            [
                {
                    "text": "📱 Driver Status",
                    "callback_data": "driver_status"
                }
            ]
        ]
    }
    
    return send_driver_message(driver_telegram_id, message, keyboard)

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
        from url_utils import construct_driver_panel_url
        webapp_url = construct_driver_panel_url(order_data['id'], driver_telegram_id)
        
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

def start_order_timer(order_id, driver_telegram_id):
    """Start 1-minute countdown timer for order acceptance"""
    def timeout_handler():
        time.sleep(60)  # 1 minute countdown
        
        # Check if order is still pending
        if order_id in pending_orders:
            logger.info(f"Order {order_id} timed out for driver {driver_telegram_id}")
            
            # Remove from pending orders
            pending_orders.pop(order_id, None)
            order_timers.pop(order_id, None)
            
            # Send timeout message to driver
            send_driver_message(driver_telegram_id, f"⏰ *Order Timeout*\n\nOrder #{order_id} has been automatically reassigned to another driver due to no response within 1 minute.")
            
            # Reassign order to next available driver
            reassign_order_to_next_driver(order_id)
    
    # Start timer thread
    timer_thread = threading.Thread(target=timeout_handler)
    timer_thread.daemon = True
    timer_thread.start()
    
    # Store timer reference
    order_timers[order_id] = timer_thread

def reassign_order_to_next_driver(order_id):
    """Reassign order to next available driver"""
    try:
        from models import Order, Driver
        from extensions import db
        
        order = Order.query.get(order_id)
        if not order or order.status != 'pending':
            return
            
        # Find next available driver
        available_drivers = Driver.query.filter_by(
            is_active=True,
            is_available=True,
            is_approved=True
        ).filter(
            Driver.current_lat.isnot(None),
            Driver.current_lng.isnot(None),
            Driver.last_location_update > datetime.utcnow() - timedelta(minutes=10)
        ).all()
        
        if available_drivers:
            # Calculate distances and find nearest driver
            restaurant_coords = (9.145, 40.489658)
            nearest_driver = None
            min_distance = float('inf')
            
            for driver in available_drivers:
                if driver.telegram_user_id in [d_id for d_id in pending_orders.values()]:
                    continue  # Skip drivers with pending orders
                    
                distance = calculate_distance(
                    restaurant_coords,
                    (driver.current_lat, driver.current_lng)
                )
                
                if distance < min_distance and distance <= 10:  # Within 10km
                    min_distance = distance
                    nearest_driver = driver
            
            if nearest_driver:
                # Notify next driver
                notify_driver_with_countdown(nearest_driver.telegram_user_id, order_id)
                logger.info(f"Order {order_id} reassigned to driver {nearest_driver.telegram_user_id}")
            else:
                # No more drivers available
                send_admin_no_drivers_notification(order_id)
                
    except Exception as e:
        logger.error(f"Error reassigning order {order_id}: {e}")

def notify_driver_with_countdown(driver_telegram_id, order_id):
    """Notify driver with countdown timer"""
    try:
        from models import Order
        
        order = Order.query.get(order_id)
        if not order:
            return
            
        # Add to pending orders
        pending_orders[order_id] = driver_telegram_id
        
        # Calculate distance
        restaurant_coords = (9.145, 40.489658)
        customer_coords = (order.location_lat or 9.165, order.location_lng or 40.510)
        distance = calculate_distance(restaurant_coords, customer_coords)
        
        message = f"🚚 *NEW DELIVERY REQUEST*\n\n"
        message += f"📋 Order #{order_id}\n"
        message += f"🏪 Restaurant: ET-FOOD Kitchen\n"
        message += f"📍 Distance to Customer: {distance:.1f} km\n\n"
        message += f"👤 Customer: {order.customer_name}\n"
        message += f"📞 Phone: {order.customer_phone}\n"
        message += f"💰 Amount: {order.total_amount:.2f} ETB\n"
        message += f"💳 Payment: {order.payment_method}\n\n"
        message += f"⏰ *You have 1 minute to respond*\n"
        message += f"🏃‍♂️ First to accept gets the order!"
        
        # Create WebApp URL using centralized URL utility
        from url_utils import construct_driver_panel_url
        webapp_url = construct_driver_panel_url(order_id, driver_telegram_id)
        
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
                        "text": "✅ ACCEPT ORDER",
                        "callback_data": f"driver_accept_{order_id}"
                    },
                    {
                        "text": "❌ REJECT",
                        "callback_data": f"driver_reject_{order_id}"
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
        
        send_driver_message(driver_telegram_id, message, keyboard)
        
        # Start 1-minute countdown
        start_order_timer(order_id, driver_telegram_id)
        
    except Exception as e:
        logger.error(f"Error notifying driver {driver_telegram_id}: {e}")

def handle_driver_callback(callback_query):
    """Handle driver bot callback queries"""
    try:
        # Use the enhanced callback handler system
        from enhanced_driver_callback_handler import handle_driver_callback as enhanced_handler
        enhanced_handler(callback_query)
        
    except Exception as e:
        logger.error(f"Error in enhanced callback handler: {e}")
        # Fallback to basic callback handling
        try:
            callback_data = callback_query.get('data', '')
            chat_id = callback_query['from']['id']
            message_id = callback_query['message']['message_id']
            
            if callback_data.startswith('driver_accept_'):
                order_id = callback_data.split('_')[2]
                from real_time_delivery_system import delivery_system
                delivery_system.handle_driver_order_acceptance(chat_id, order_id)
                
            elif callback_data.startswith('driver_reject_'):
                order_id = callback_data.split('_')[2]
                from real_time_delivery_system import delivery_system
                delivery_system.handle_driver_order_rejection(chat_id, order_id)
                
            elif callback_data.startswith('accept_order_'):
                order_id = callback_data.split('_')[2]
                from real_time_delivery_system import delivery_system
                delivery_system.handle_driver_order_acceptance(chat_id, order_id)
                
            elif callback_data.startswith('decline_order_'):
                order_id = callback_data.split('_')[2]
                from real_time_delivery_system import delivery_system
                delivery_system.handle_driver_order_rejection(chat_id, order_id)
                
            elif callback_data.startswith('driver_location_'):
                order_id = callback_data.split('_')[2]
                request_driver_location_sharing(chat_id, order_id)
                
            elif callback_data.startswith('call_restaurant_'):
                send_driver_message(chat_id, "📞 *Restaurant Contact*\n\nET-FOOD Kitchen\nPhone: +251-911-123-456\n\nPlease call to coordinate order pickup.")
                
            elif callback_data.startswith('call_customer_'):
                order_id = callback_data.split('_')[2]
                try:
                    from models import Order
                    order = Order.query.get(order_id)
                    if order:
                        send_driver_message(chat_id, f"📞 *Customer Contact*\n\nName: {order.customer_name}\nPhone: {order.customer_phone}\n\nPlease call to coordinate delivery.")
                    else:
                        send_driver_message(chat_id, "❌ Order not found.")
                except Exception as e:
                    send_driver_message(chat_id, "❌ Error retrieving customer contact.")
                    
            # New inline button handlers
            elif callback_data == 'driver_status':
                send_driver_status_message(chat_id)
                
            elif callback_data == 'driver_orders':
                send_driver_orders(chat_id)
                
            elif callback_data == 'toggle_availability':
                toggle_driver_availability(chat_id)
                
            elif callback_data == 'driver_earnings':
                send_driver_earnings(chat_id)
                
            elif callback_data == 'driver_help':
                send_driver_help_message(chat_id)
                
            elif callback_data == 'request_location':
                send_location_request(chat_id)
                
            elif callback_data == 'enable_live_location':
                send_live_location_instructions(chat_id)
                
            elif callback_data == 'contact_support':
                send_driver_message(chat_id, "📞 *ET-FOOD Support*\n\nFor assistance, please contact:\n📧 Email: support@etfood.com\n📞 Phone: +251-911-123-456\n\nOur team is available 24/7 to help you!")
                
            elif callback_data.startswith('share_location_'):
                send_location_request(chat_id)
                
            elif callback_data.startswith('pickup_complete_'):
                order_id = callback_data.split('_')[2]
                from real_time_delivery_system import delivery_system
                delivery_system.handle_pickup_completion(chat_id, order_id)
                
            elif callback_data.startswith('delivery_complete_'):
                order_id = callback_data.split('_')[2]
                from real_time_delivery_system import delivery_system
                delivery_system.handle_delivery_completion(chat_id, order_id)
                
            elif callback_data.startswith('driver_panel_'):
                order_id = callback_data.split('_')[2]
                from driver_gps_panel import send_driver_gps_panel
                send_driver_gps_panel(chat_id, order_id)
                
            elif callback_data.startswith('navigate_customer_'):
                order_id = callback_data.split('_')[2]
                from driver_gps_panel import handle_navigate_to_customer
                handle_navigate_to_customer(chat_id, order_id)
                
            elif callback_data.startswith('navigate_restaurant'):
                from driver_gps_panel import handle_navigate_to_restaurant
                handle_navigate_to_restaurant(chat_id)
                
            elif callback_data.startswith('call_customer_'):
                order_id = callback_data.split('_')[2]
                from driver_gps_panel import handle_call_customer
                handle_call_customer(chat_id, order_id)
                
            elif callback_data == 'call_restaurant':
                from driver_gps_panel import handle_call_restaurant
                handle_call_restaurant(chat_id)
                
            elif callback_data.startswith('share_location_'):
                # Handle location sharing request
                order_id = callback_data.split('_')[2]
                send_driver_message(chat_id, "📍 Please share your live location using the 📎 attachment button → Location → Share Live Location (for delivery tracking)")
                
            elif callback_data == 'share_location':
                # Handle general location sharing request
                send_driver_message(chat_id, "📍 Please share your live location using the 📎 attachment button → Location → Share Live Location")
                
            elif callback_data == 'start_registration':
                handle_start_registration(chat_id)
                
            elif callback_data == 'link_account':
                handle_link_account(chat_id)
                
            elif callback_data == 'share_contact_for_registration':
                send_driver_contact_request(chat_id)
                
            elif callback_data == 'type_phone_number':
                send_driver_message(chat_id, "📱 *Manual Phone Number Entry*\n\nPlease type your phone number in the format: +251912345678\n\n🔹 Include country code (+251 for Ethiopia)\n🔹 No spaces or special characters\n🔹 Example: +251911234567\n\nType your phone number now:")
                
            elif callback_data == 'back_to_registration':
                send_driver_registration_options(chat_id)
                
            elif callback_data == 'toggle_status':
                toggle_driver_availability(chat_id)
                
            elif callback_data == 'view_earnings':
                send_driver_earnings(chat_id)
                
            elif callback_data == 'view_orders':
                send_driver_orders(chat_id)
                
            # Enhanced callback handlers for complete delivery workflow
            elif callback_data.startswith('pickup_complete_'):
                order_id = callback_data.split('_')[2]
                handle_pickup_complete(chat_id, order_id)
                
            elif callback_data.startswith('delivery_complete_'):
                order_id = callback_data.split('_')[2]
                from enhanced_driver_system import handle_delivery_completion_workflow
                handle_delivery_completion_workflow(chat_id, order_id)
                
            elif callback_data.startswith('driver_panel_'):
                order_id = callback_data.split('_')[2]
                from driver_gps_panel import send_driver_gps_panel
                send_driver_gps_panel(chat_id, order_id)
                
            elif callback_data.startswith('call_customer_'):
                order_id = callback_data.split('_')[2]
                from driver_gps_panel import handle_call_customer
                handle_call_customer(chat_id, order_id)
                
            elif callback_data.startswith('navigate_customer_'):
                order_id = callback_data.split('_')[2]
                from driver_gps_panel import handle_navigate_to_customer
                handle_navigate_to_customer(chat_id, order_id)
                
            elif callback_data == 'driver_status':
                send_driver_status_message(chat_id)
                
            elif callback_data == 'driver_orders':
                send_driver_orders(chat_id)
                
            elif callback_data == 'driver_earnings':
                send_driver_earnings(chat_id)
                
            elif callback_data == 'driver_help':
                send_driver_help_message(chat_id)
                
            elif callback_data == 'toggle_availability':
                toggle_driver_availability(chat_id)
                
            elif callback_data == 'request_location':
                send_location_request(chat_id)
                
            elif callback_data == 'enable_live_location':
                send_live_location_instructions(chat_id)
                
            elif callback_data == 'contact_support':
                send_driver_message(chat_id, "📞 *Contact Support*\n\nFor assistance, please contact:\n📱 Admin: +251911234567\n✉️ Email: support@et-food.com\n\nOr message admin directly through this bot.")
                
            # Handle order acceptance/rejection (main functionality)
            elif callback_data.startswith('driver_accept_'):
                # Use enhanced callback handler for order acceptance
                from enhanced_driver_callback_handler import handle_driver_callback
                handle_driver_callback(callback_query)
                return  # Exit here to avoid duplicate handling
                
            elif callback_data.startswith('driver_decline_'):
                # Use enhanced callback handler for order rejection
                from enhanced_driver_callback_handler import handle_driver_callback
                handle_driver_callback(callback_query)
                return  # Exit here to avoid duplicate handling
                
            # Answer callback query
            answer_callback_query(callback_query['id'], "Action processed!")
            
        except Exception as inner_e:
            logger.error(f"Error in fallback callback handler: {inner_e}")
            
    except Exception as e:
        logger.error(f"Error handling driver callback: {e}")

def send_location_request(chat_id):
    """Send location request message to driver"""
    message = "📍 *Location Sharing Required for Order Assignments*\n\n"
    message += "🚨 **IMPORTANT**: You must share your location to receive delivery orders!\n\n"
    message += "📍 Location sharing enables:\n"
    message += "✅ Automatic order notifications in your area\n"
    message += "✅ Distance-based order matching\n"
    message += "✅ Real-time delivery tracking\n"
    message += "✅ Admin monitoring for your safety\n\n"
    message += "👇 **Tap the button below to share your live location:**"
    
    keyboard = {
        "keyboard": [
            [
                {
                    "text": "📍 Share My Live Location",
                    "request_location": True
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
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
    """Handle order acceptance by driver with complete automated workflow"""
    try:
        from models import Order, Driver
        from app import app, db
        from bot_minimal import send_message
        
        with app.app_context():
            # Find driver by telegram ID
            driver = Driver.query.filter_by(telegram_user_id=driver_chat_id).first()
            if not driver:
                send_driver_message(driver_chat_id, "❌ Driver not found in system. Please contact admin.")
                return False
                
            # Find order
            order = db.session.get(Order, order_id)
            if not order:
                send_driver_message(driver_chat_id, "❌ Order not found.")
                return False
                
            # Check if order is still available for assignment
            if order.status not in ['confirmed', 'preparing']:
                send_driver_message(driver_chat_id, f"❌ Order #{order_id} is no longer available (Status: {order.status})")
                return False
                
            # STEP 1: Assign driver to order
            order.driver_id = driver.id
            order.status = 'out_for_delivery'
            
            # STEP 2: Update driver availability
            driver.is_available = False
            
            db.session.commit()
            
            # STEP 3: Send acceptance confirmation first
            send_driver_message(driver_chat_id, f"✅ *Order #{order_id} Accepted!*\n\n🚚 You are now assigned to this delivery.\n📍 Opening driver panel with GPS navigation...")
            
            # STEP 4: Send complete customer information with driver panel
            send_complete_customer_info_to_driver(driver_chat_id, order_id)
            
            # STEP 5: Notify customer about driver assignment
            notify_customer_about_driver_assignment(order_id, driver.name, driver.telegram_user_id)
            
            # STEP 6: Notify admin about assignment and enable live tracking
            notify_admin_driver_assignment_with_tracking(order_id, driver.name, driver.telegram_user_id)
            
            logger.info(f"Order {order_id} successfully assigned to driver {driver.name} - Full workflow completed")
            return True
        
    except Exception as e:
        logger.error(f"Error handling order acceptance: {e}")
        return False

def handle_order_rejection(driver_chat_id, order_id, message_id):
    """Handle order rejection by driver and reassign to next available driver"""
    try:
        from complete_order_workflow import OrderWorkflowManager
        
        # Send confirmation to rejecting driver
        message = f"❌ *Order Rejected*\n\n"
        message += f"📋 Order #{order_id} has been rejected.\n"
        message += f"🔄 The order will be reassigned to another driver.\n\n"
        message += f"Thank you for your response!"
        
        send_driver_message(driver_chat_id, message)
        
        # Automatically reassign to next available driver
        workflow = OrderWorkflowManager()
        workflow.reassign_to_next_driver(order_id, exclude_driver_id=driver_chat_id)
        
        logger.info(f"Order {order_id} rejected by driver {driver_chat_id} and reassigned")
        
    except Exception as e:
        logger.error(f"Error handling order rejection: {e}")

def send_complete_customer_info_to_driver(driver_telegram_id, order_id):
    """Send complete customer information to driver"""
    try:
        from models import Order
        from app import app, db
        import json
        
        with app.app_context():
            order = db.session.get(Order, order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            # Parse order items
            items_list = []
            if order.items:
                try:
                    items_data = json.loads(order.items) if isinstance(order.items, str) else order.items
                    for item in items_data:
                        items_list.append(f"• {item['name']} x{item['quantity']} - {item['price']:.2f} ETB")
                except:
                    items_list.append("• Order items (details unavailable)")
            
            # Create comprehensive message
            message = f"🎯 *ORDER ASSIGNMENT CONFIRMED*\n\n"
            message += f"📋 **Order Details:**\n"
            message += f"• Order ID: #{order_id}\n"
            message += f"• Status: ASSIGNED TO YOU\n"
            message += f"• Time: {order.created_at.strftime('%I:%M %p')}\n"
            message += f"• Total: {order.total_amount:.2f} ETB\n"
            message += f"• Payment: {order.payment_method}\n\n"
            
            message += f"👤 **Customer Information:**\n"
            message += f"• Name: {order.customer_name}\n"
            message += f"• Phone: {order.customer_phone}\n"
            message += f"• Address: {order.customer_address}\n"
            if order.location_lat and order.location_lng:
                message += f"• GPS: {order.location_lat:.6f}, {order.location_lng:.6f}\n"
            message += f"\n"
            
            message += f"🛍️ **Order Items:**\n"
            message += "\n".join(items_list)
            message += f"\n\n"
            
            message += f"📍 **Next Steps:**\n"
            message += f"1. Open Driver Panel for live GPS navigation\n"
            message += f"2. Share your live location for tracking\n"
            message += f"3. Contact customer if needed\n"
            message += f"4. Pick up order from restaurant\n"
            message += f"5. Deliver to customer address"
            
            # Add action buttons
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order_id}"
                        },
                        {
                            "text": "📍 Open Maps",
                            "url": f"https://maps.google.com/?q={order.location_lat},{order.location_lng}" if order.location_lat else "https://maps.google.com"
                        }
                    ],
                    [
                        {
                            "text": "✅ Pickup Complete",
                            "callback_data": f"pickup_complete_{order_id}"
                        },
                        {
                            "text": "🚚 Delivered",
                            "callback_data": f"delivery_complete_{order_id}"
                        }
                    ],
                    [
                        {
                            "text": "📍 Share Live Location",
                            "callback_data": "request_location"
                        },
                        {
                            "text": "🗺️ Driver Panel (GPS)",
                            "callback_data": f"driver_panel_{order_id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver_telegram_id, message, keyboard=keyboard)
            return True
            
    except Exception as e:
        logger.error(f"Error sending customer info to driver: {e}")
        return False

def notify_customer_about_driver_assignment(order_id, driver_name, driver_telegram_id):
    """Notify customer about driver assignment with tracking info"""
    try:
        from models import Order
        from app import app, db
        from bot_minimal import send_message
        
        with app.app_context():
            order = db.session.get(Order, order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            message = f"🚚 *Driver Assigned to Your Order!*\n\n"
            message += f"🚗 Driver: {driver_name}\n"
            message += f"💰 Total: {order.total_amount:.2f} ETB\n\n"
            message += f"📍 Your driver will share live location for real-time tracking.\n"
            message += f"📞 You can contact the driver if needed.\n\n"
            message += f"🕐 Estimated delivery: 15-30 minutes\n"
            message += f"✅ Order status: Out for delivery"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📍 Track Driver",
                            "url": f"https://maps.google.com"
                        },
                        {
                            "text": "📞 Call Driver",
                            "url": f"tg://user?id={driver_telegram_id}"
                        }
                    ]
                ]
            }
            
            send_message(order.telegram_user_id, message, keyboard=keyboard)
            logger.info(f"Customer {order.customer_name} notified about driver assignment")
            return True
            
    except Exception as e:
        logger.error(f"Error notifying customer about driver assignment: {e}")
        return False

def notify_admin_driver_assignment_with_tracking(order_id, driver_name, driver_telegram_id):
    """Notify admin about driver assignment and enable live tracking"""
    try:
        from models import AdminUser, Order
        from app import app, db
        from bot_minimal import send_message_to_admin
        
        with app.app_context():
            order = db.session.get(Order, order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            # Send to all active admins
            admins = AdminUser.query.filter_by(is_active=True).all()
            
            message = f"✅ *Driver Assignment Successful*\n\n"
            message += f"📋 **Order #{order_id}**\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
            message += f"🚗 **Assigned Driver:**\n"
            message += f"• Name: {driver_name}\n"
            message += f"• Telegram ID: {driver_telegram_id}\n\n"
            message += f"📍 **Live Tracking Available**\n"
            message += f"• Driver location will update automatically\n"
            message += f"• Customer has been notified\n"
            message += f"• Order status: Out for delivery"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📍 Track Driver Location",
                            "url": f"https://maps.google.com"
                        },
                        {
                            "text": "📱 Contact Driver",
                            "url": f"tg://user?id={driver_telegram_id}"
                        }
                    ]
                ]
            }
            
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, message, keyboard=keyboard)
            
            logger.info(f"Admin notified about driver assignment for Order {order_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error notifying admin about driver assignment: {e}")
        return False

def request_live_location_for_delivery(driver_telegram_id, order_id):
    """Request driver to start live location sharing for delivery tracking"""
    try:
        message = f"📍 *Start Live Location Sharing*\n\n"
        message += f"🚚 **Order #{order_id} - Delivery in Progress**\n\n"
        message += f"Please share your live location so:\n"
        message += f"✅ Customer can track your progress\n"
        message += f"✅ Admin can monitor delivery\n"
        message += f"✅ System can provide accurate ETAs\n\n"
        message += f"🔄 **How to share live location:**\n"
        message += f"1. Tap the button below\n"
        message += f"2. Select 'Share Live Location'\n"
        message += f"3. Choose duration (30 min recommended)\n"
        message += f"4. Tap 'Send'\n\n"
        message += f"⚠️ Keep location sharing ON until delivery is complete!"
        
        keyboard = {
            "keyboard": [
                [
                    {
                        "text": "📍 Share Live Location for Delivery",
                        "request_location": True
                    }
                ]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        send_driver_message(driver_telegram_id, message, keyboard=keyboard)
        logger.info(f"Live location request sent to driver for Order {order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error requesting live location: {e}")
        return False

def handle_pickup_complete(chat_id, order_id):
    """Handle pickup completion notification"""
    try:
        from models import Order, Driver
        from app import app, db
        from bot_minimal import send_message_to_admin, send_message
        
        with app.app_context():
            # Find order and driver
            order = db.session.get(Order, order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                send_driver_message(chat_id, "❌ Order or driver not found.")
                return False
            
            # Update order status
            order.status = 'out_for_delivery'
            order.pickup_time = datetime.utcnow()
            db.session.commit()
            
            # Notify driver
            message = f"✅ *Pickup Confirmed*\n\n"
            message += f"📋 Order #{order_id} pickup confirmed\n"
            message += f"🚚 Status: Out for delivery\n"
            message += f"📍 Now navigate to customer location\n\n"
            message += f"🎯 **Next Steps:**\n"
            message += f"• Share your live location for tracking\n"
            message += f"• Navigate to customer address\n"
            message += f"• Contact customer if needed\n"
            message += f"• Complete delivery"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "url": f"tel:{order.customer_phone}"
                        },
                        {
                            "text": "📍 Navigate",
                            "url": f"https://maps.google.com/?q={order.location_lat},{order.location_lng}" if order.location_lat else "https://maps.google.com"
                        }
                    ],
                    [
                        {
                            "text": "📍 Share Live Location",
                            "callback_data": "request_location"
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
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
            # Notify customer
            customer_message = f"🚚 *Your Order is Out for Delivery!*\n\n"
            customer_message += f"📋 Order #{order_id}\n"
            customer_message += f"🚗 Driver: {driver.name}\n"
            customer_message += f"📍 Your order has been picked up and is on the way!\n\n"
            customer_message += f"🕐 Estimated delivery: 10-20 minutes\n"
            customer_message += f"📞 You can track the driver's location in real-time"
            
            send_message(order.telegram_user_id, customer_message)
            
            # Notify admin
            admin_message = f"🚚 *Pickup Complete*\n\n"
            admin_message += f"📋 Order #{order_id}\n"
            admin_message += f"🚗 Driver: {driver.name}\n"
            admin_message += f"👤 Customer: {order.customer_name}\n"
            admin_message += f"📞 Phone: {order.customer_phone}\n"
            admin_message += f"📍 Status: Out for delivery\n\n"
            admin_message += f"⏰ Pickup Time: {order.pickup_time.strftime('%I:%M %p')}"
            
            from models import AdminUser
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, admin_message)
            
            logger.info(f"Pickup completed for Order {order_id} by driver {driver.name}")
            return True
            
    except Exception as e:
        logger.error(f"Error handling pickup completion: {e}")
        return False

def handle_delivery_complete(chat_id, order_id):
    """Handle delivery completion"""
    try:
        from models import Order, Driver
        from app import app, db
        from bot_minimal import send_message_to_admin, send_message
        
        with app.app_context():
            # Find order and driver
            order = db.session.get(Order, order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                send_driver_message(chat_id, "❌ Order or driver not found.")
                return False
            
            # Update order status
            order.status = 'delivered'
            order.updated_at = datetime.utcnow()
            
            # Make driver available again
            driver.is_available = True
            
            db.session.commit()
            
            # Calculate delivery time
            delivery_duration = ""
            if hasattr(order, 'pickup_time') and order.pickup_time:
                duration = order.updated_at - order.pickup_time
                minutes = int(duration.total_seconds() / 60)
                delivery_duration = f"{minutes} minutes"
            
            # Notify driver with customer rating display
            message = f"🎉 *Delivery Completed Successfully!*\n\n"
            message += f"📋 Order #{order_id} delivered\n"
            message += f"✅ Status: Completed\n"
            message += f"⏰ Delivery time: {delivery_duration}\n"
            message += f"💰 Payment: {order.payment_method}\n\n"
            message += f"👤 **Customer:** {order.customer_name}\n"
            message += f"📞 **Phone:** {order.customer_phone}\n"
            message += f"⭐ **Customer will rate this delivery**\n\n"
            message += f"🎯 **Great job!** You're automatically available for new orders.\n"
            message += f"📊 Check your earnings and wait for next delivery assignment."
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📊 View Earnings",
                            "callback_data": "driver_earnings"
                        },
                        {
                            "text": "📋 View Orders",
                            "callback_data": "driver_orders"
                        }
                    ],
                    [
                        {
                            "text": "🔄 Check Status",
                            "callback_data": "driver_status"
                        },
                        {
                            "text": "📍 Share Location",
                            "callback_data": "request_location"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
            # Notify customer with detailed delivery confirmation
            customer_message = f"🎉 *Your Order Has Been Delivered Successfully!*\n\n"
            customer_message += f"📋 **Order #{order_id}**\n"
            customer_message += f"🚗 **Driver:** {driver.name}\n"
            customer_message += f"✅ **Status:** Delivered\n"
            customer_message += f"💰 **Total:** {order.total_amount:.2f} ETB\n"
            customer_message += f"💳 **Payment:** {order.payment_method}\n"
            if delivery_duration:
                customer_message += f"⏰ **Delivery Time:** {delivery_duration}\n"
            customer_message += f"🕐 **Completed At:** {order.updated_at.strftime('%I:%M %p')}\n\n"
            customer_message += f"🌟 **Thank you for choosing ET-FOOD!**\n"
            customer_message += f"📝 We'd love to hear your feedback about this order.\n"
            customer_message += f"⭐ Rate your experience and help us improve our service!"
            
            # Add customer feedback buttons with order again option
            customer_keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "⭐⭐⭐⭐⭐ Excellent",
                            "callback_data": f"rate_order_{order_id}_5"
                        },
                        {
                            "text": "⭐⭐⭐⭐ Good",
                            "callback_data": f"rate_order_{order_id}_4"
                        }
                    ],
                    [
                        {
                            "text": "⭐⭐⭐ Average",
                            "callback_data": f"rate_order_{order_id}_3"
                        },
                        {
                            "text": "⭐⭐ Poor",
                            "callback_data": f"rate_order_{order_id}_2"
                        }
                    ],
                    [
                        {
                            "text": "📝 Leave Feedback",
                            "callback_data": f"feedback_{order_id}"
                        },
                        {
                            "text": "🍽️ Order Again",
                            "callback_data": "open_menu_again"
                        }
                    ]
                ]
            }
            
            send_message(order.telegram_user_id, customer_message, keyboard=customer_keyboard)
            
            # Notify admin with comprehensive delivery report
            admin_message = f"✅ **DELIVERY COMPLETED SUCCESSFULLY**\n\n"
            admin_message += f"📋 **Order Details:**\n"
            admin_message += f"• Order ID: #{order_id}\n"
            admin_message += f"• Customer: {order.customer_name}\n"
            admin_message += f"• Phone: {order.customer_phone}\n"
            admin_message += f"• Address: {order.customer_address}\n"
            admin_message += f"• Total: {order.total_amount:.2f} ETB\n"
            admin_message += f"• Payment: {order.payment_method}\n\n"
            admin_message += f"🚗 **Driver Information:**\n"
            admin_message += f"• Driver: {driver.name}\n"
            admin_message += f"• Phone: {driver.phone_number}\n"
            admin_message += f"• Vehicle: {driver.vehicle_type}\n\n"
            admin_message += f"⏰ **Delivery Timeline:**\n"
            admin_message += f"• Order placed: {order.created_at.strftime('%I:%M %p')}\n"
            if order.pickup_time:
                admin_message += f"• Pickup completed: {order.pickup_time.strftime('%I:%M %p')}\n"
            admin_message += f"• Delivery completed: {order.delivery_time.strftime('%I:%M %p')}\n"
            if delivery_duration:
                admin_message += f"• Delivery duration: {delivery_duration}\n\n"
            admin_message += f"🎉 **Order delivered successfully!**\n"
            admin_message += f"📊 Driver is now available for new assignments."
            
            # Add admin action buttons
            admin_keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📊 View Order Details",
                            "callback_data": f"view_order_{order_id}"
                        },
                        {
                            "text": "📈 Daily Report",
                            "callback_data": "daily_report"
                        }
                    ],
                    [
                        {
                            "text": "🚗 Driver Status",
                            "callback_data": f"driver_status_{driver.id}"
                        }
                    ]
                ]
            }
            
            from models import AdminUser
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, admin_message, keyboard=admin_keyboard)
            
            logger.info(f"Order {order_id} delivered successfully by driver {driver.name} - All notifications sent")
            return True
            
    except Exception as e:
        logger.error(f"Error handling delivery completion: {e}")
        return False

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

def handle_driver_contact_registration_flow(chat_id, contact, user_data):
    """Handle contact sharing for either new registration or existing driver linking"""
    try:
        from models import Driver
        from extensions import db
        from main import app
        
        with app.app_context():
            phone_number = contact['phone_number']
            
            # Check if this is for new registration (specific context)
            # For now, we'll handle both cases in the same flow
            existing_driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if existing_driver:
                # Driver already linked
                send_driver_welcome_message(chat_id, existing_driver)
                return
            
            # Try to find driver by phone number
            clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
            driver = Driver.query.filter(
                Driver.phone_number.like(f'%{clean_phone[-10:]}%')
            ).first()
            
            if driver:
                # Link existing driver
                driver.telegram_user_id = chat_id
                db.session.commit()
                send_driver_welcome_message(chat_id, driver)
            else:
                # New driver registration flow
                from driver_registration import handle_driver_contact_registration
                handle_driver_contact_registration(chat_id, contact, user_data)
                
    except Exception as e:
        logger.error(f"Error in contact registration flow: {e}")
        send_driver_message(chat_id, "❌ Error processing contact. Please try again.")

def handle_driver_contact_share(chat_id, contact):
    """Handle driver contact sharing and automatic registration"""
    try:
        from models import Driver
        from extensions import db
        from app import app
        
        with app.app_context():
            phone_number = contact['phone_number']
            first_name = contact.get('first_name', '')
            
            # Try to find existing driver by phone number (match last 10 digits)
            clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
            driver = Driver.query.filter(
                Driver.phone_number.like(f'%{clean_phone[-10:]}%')
            ).first()
            
            if driver:
                # Link existing driver to this Telegram account
                driver.telegram_user_id = chat_id
                db.session.commit()
                
                # Send welcome message with driver info
                message = f"✅ *Welcome back, {driver.name}!*\n\n"
                message += f"📱 Your Telegram account has been linked to your driver profile.\n\n"
                message += f"🚗 Vehicle Type: {driver.vehicle_type or 'Not specified'}\n"
                if driver.is_approved:
                    message += f"✅ Status: Approved and Active\n"
                else:
                    message += f"⏳ Status: Pending approval\n"
                
                message += f"\n🎯 You can now receive order notifications!\n"
                message += f"📍 Please share your location to start receiving orders."
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📍 Share Location",
                                "callback_data": "request_location"
                            }
                        ],
                        [
                            {
                                "text": "📊 View Status",
                                "callback_data": "driver_status"
                            }
                        ]
                    ]
                }
                
                send_driver_message(chat_id, message, keyboard=keyboard)
                
                # Send notification to admin about successful linking
                notify_admin_driver_link(driver.name, phone_number, chat_id)
                
            else:
                # No existing driver found - show registration form
                send_driver_registration_form(chat_id, phone_number, first_name)
                
    except Exception as e:
        logger.error(f"Error handling driver contact share: {e}")
        send_driver_message(chat_id, "❌ Error processing contact. Please try again or contact admin.")

def notify_admin_new_driver_attempt(chat_id, phone_number, first_name):
    """Notify admin about new driver registration attempt"""
    try:
        from models import AdminUser
        from main import app
        from bot_minimal import send_message_to_admin
        
        with app.app_context():
            admins = AdminUser.query.filter_by(is_active=True).all()
            
            message = f"👤 *New Driver Registration Attempt*\n\n"
            message += f"📞 Phone: {phone_number}\n"
            message += f"👤 Name: {first_name}\n"
            message += f"🆔 Telegram ID: {chat_id}\n\n"
            message += f"This user tried to register with the driver bot but was not found in the system.\n\n"
            message += f"To register this driver:\n"
            message += f"1. Go to Admin Dashboard → Drivers\n"
            message += f"2. Click 'Add Driver Employee'\n"
            message += f"3. Enter details with phone: {phone_number}\n"
            message += f"4. Use Telegram ID: {chat_id}\n"
            message += f"5. Driver will be automatically notified"
            
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, message)
                
    except Exception as e:
        logger.error(f"Error notifying admin about new driver: {e}")

def notify_admin_driver_link(driver_name, phone_number, telegram_id):
    """Notify admin about successful driver Telegram account linking"""
    try:
        from models import AdminUser
        from app import app
        from bot_minimal import send_message_to_admin
        
        with app.app_context():
            message = f"✅ *Driver Account Linked Successfully*\n\n"
            message += f"👤 Driver: {driver_name}\n"
            message += f"📱 Phone: {phone_number}\n"
            message += f"🆔 Telegram ID: {telegram_id}\n\n"
            message += f"🎯 Driver can now receive order notifications automatically.\n"
            message += f"📍 Waiting for location sharing to enable order assignments."
            
            # Send to all active admins
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, message)
            
    except Exception as e:
        logger.error(f"Error notifying admin about driver link: {e}")

def handle_driver_location_update(chat_id, location):
    """Handle driver location update"""
    try:
        from models import Driver
        from app import db
        from main import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            if driver:
                driver.current_lat = location['latitude']
                driver.current_lng = location['longitude']
                driver.last_location_update = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Location updated for driver {driver.name} (ID: {chat_id}): {driver.current_lat}, {driver.current_lng}")
                
                send_driver_message(chat_id, f"📍 Location updated successfully!\n\n✅ **Admin can now track your delivery**\n📍 GPS: {driver.current_lat:.4f}, {driver.current_lng:.4f}\n⏰ Updated: {driver.last_location_update.strftime('%H:%M:%S')}\n\n⚠️ **Keep sharing your location regularly** to receive order assignments in your area.")
            else:
                logger.warning(f"Driver not found for Telegram ID: {chat_id}")
                send_driver_message(chat_id, "❌ Driver profile not found. Please contact admin or use /start to register.")
            
    except Exception as e:
        logger.error(f"Error updating driver location for {chat_id}: {e}")
        send_driver_message(chat_id, "❌ Failed to update location. Please try again or contact support.")

def init_driver_bot(flask_app):
    """Initialize the driver bot with Flask app context"""
    global _driver_bot_initialized
    
    # Prevent duplicate initialization
    if _driver_bot_initialized:
        logger.info("Driver bot already initialized, skipping...")
        return
    
    with flask_app.app_context():
        logger.info("Initializing Driver Telegram bot...")
        
        # Set up webhook
        setup_driver_webhook(flask_app)
        
        # Mark as initialized
        _driver_bot_initialized = True
        logger.info("Driver bot initialized successfully!")

def setup_driver_webhook(flask_app):
    """Set up webhook for the driver bot"""
    # Prevent duplicate route registration by checking Flask's view functions
    if "driver_webhook" in flask_app.view_functions:
        logger.info("Driver webhook route already registered, skipping...")
        return
    
    with flask_app.app_context():
        @flask_app.route('/driver-webhook', methods=['POST'])
        def driver_webhook():
            """Handle driver bot webhook"""
            try:
                update = request.get_json()
                
                if 'message' in update:
                    message = update['message']
                    chat_id = message['from']['id']
                    
                    # Handle location updates (both regular and live location)
                    if 'location' in message:
                        logger.info(f"Received location from driver {chat_id}: {message['location']}")
                        handle_driver_location_update(chat_id, message['location'])
                    elif 'contact' in message:
                        # Check if this is for registration or existing driver linking
                        user_data = message.get('from', {})
                        handle_driver_contact_registration_flow(chat_id, message['contact'], user_data)
                    elif 'text' in message:
                        handle_driver_text_message(chat_id, message['text'])
                        
                elif 'callback_query' in update:
                    handle_driver_callback(update['callback_query'])
                    
                return jsonify({'status': 'ok'})
                
            except Exception as e:
                logger.error(f"Error processing driver webhook: {e}")
                return jsonify({'error': str(e)}), 500
        
        # Log successful route registration
        logger.info("Driver webhook route registered successfully")
        
        # Set webhook with delay to allow host resolution
        import threading
        import time
        
        def delayed_webhook_setup():
            """Set up webhook after a delay to ensure host resolution"""
            time.sleep(3)  # Wait 3 seconds for host to be ready
            
            # Always attempt to set webhook in both production and development
            # Special handling for production environment
            if os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('WEBHOOK_URL'):
                logger.info("Production environment detected - setting driver webhook")
                success = set_driver_webhook()
                if not success:
                    logger.error("Driver webhook setup failed in production environment")
                else:
                    logger.info("Driver webhook setup completed successfully in production")
            else:
                # Development environment
                success = set_driver_webhook()
                if not success:
                    logger.warning("Driver webhook setup failed, but continuing with application startup")
                else:
                    logger.info("Driver webhook setup completed successfully")
        
        # Start webhook setup in background thread
        webhook_thread = threading.Thread(target=delayed_webhook_setup)
        webhook_thread.daemon = True
        webhook_thread.start()

def handle_driver_text_message(chat_id, text):
    """Handle text messages from drivers"""
    if text == '/start':
        # Check if driver exists, if not, request contact sharing
        check_driver_registration_and_welcome(chat_id)
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
    elif text == "✍️ Type Phone Number Instead":
        # iOS-compatible phone number input
        message = "📱 *Manual Phone Number Entry*\n\n"
        message += "Please type your phone number in the format: +251912345678\n\n"
        message += "🔹 Include country code (+251 for Ethiopia)\n"
        message += "🔹 No spaces or special characters\n"
        message += "🔹 Example: +251911234567\n\n"
        message += "Type your phone number now:"
        
        send_driver_message(chat_id, message, keyboard={"remove_keyboard": True})
    elif text.startswith('+251') or text.startswith('251') or text.startswith('09'):
        # Handle manually typed phone numbers (iOS compatibility)
        handle_manual_phone_input(chat_id, text)
    elif text == '/test':
        # Enhanced test command with system status
        try:
            from models import Driver
            from main import app
            
            with app.app_context():
                driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
                
                test_message = "🔧 *Driver Bot System Test*\n\n"
                test_message += "✅ Bot connection: Working\n"
                test_message += "✅ Database connection: Active\n"
                test_message += "✅ Webhook integration: Functional\n"
                test_message += f"✅ Driver profile: {'Found' if driver else 'Not registered'}\n"
                test_message += f"✅ Location tracking: {'Active' if driver and driver.last_location_update else 'Inactive'}\n\n"
                test_message += f"🤖 Bot version: ET-FOOD v2.0\n"
                test_message += f"⏰ Test time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                
                if driver:
                    test_message += f"👤 Your profile: {driver.name}\n"
                    test_message += f"📞 Phone: {driver.phone_number}\n"
                    test_message += f"🎯 Status: {'Approved' if driver.is_approved else 'Pending'}"
                else:
                    test_message += "⚠️ No driver profile found. Use /start to register."
                
                send_driver_message(chat_id, test_message)
                
        except Exception as e:
            send_driver_message(chat_id, f"❌ System test failed: {str(e)}\n\nPlease contact support.")
    else:
        send_driver_message(chat_id, "🤖 I'm the ET-FOOD Driver Bot!\n\nI'll notify you about new delivery assignments. Use /help for more information.")

def check_driver_registration_and_welcome(chat_id):
    """Check if driver is registered and send appropriate welcome message"""
    try:
        from models import Driver
        from app import app
        from extensions import db
        
        with app.app_context():
            # First check if driver is already linked to this Telegram ID
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if driver and driver.is_approved:
                # Driver is approved, send welcome message
                send_driver_welcome_message(chat_id, driver)
            elif driver and not driver.is_approved:
                # Driver exists but not approved
                send_pending_approval_message(chat_id, driver)
            else:
                # Driver not found - offer contact sharing for both existing/new drivers
                send_driver_contact_request(chat_id)
                
    except Exception as e:
        logger.error(f"Error checking driver registration: {e}")
        send_driver_message(chat_id, "❌ Error checking registration. Please try again later.")

def send_pending_approval_message(chat_id, driver):
    """Send message to driver waiting for approval"""
    message = f"⏳ *Registration Under Review*\n\n"
    message += f"Hello {driver.name}!\n\n"
    message += f"📋 Your driver registration is being reviewed by our admin team.\n"
    message += f"🚗 Vehicle: {driver.vehicle_type}\n"
    message += f"📞 Phone: {driver.phone_number}\n\n"
    message += f"⏰ **Status:** {driver.approval_status.title()}\n\n"
    message += f"📢 You'll receive a notification once your registration is approved.\n"
    message += f"📞 Contact admin if you have any questions.\n\n"
    message += f"Thank you for your patience!"
    
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
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_simple_contact_admin_message(chat_id):
    """Send simple message for unregistered drivers"""
    message = f"🚚 *Welcome to ET-FOOD Driver Bot!*\n\n"
    message += f"👋 Hello! This bot is for registered ET-FOOD delivery drivers only.\n\n"
    message += f"📋 **To become a driver:**\n"
    message += f"• Contact our admin team\n"
    message += f"• Complete the registration process\n"
    message += f"• Get approved by management\n\n"
    message += f"📞 **Contact Information:**\n"
    message += f"• Phone: +251-XXX-XXXX\n"
    message += f"• Ask for driver registration\n\n"
    message += f"✅ Once approved, you'll be able to receive delivery assignments through this bot.\n\n"
    message += f"Thank you for your interest in joining ET-FOOD!"
    
    send_driver_message(chat_id, message)

def send_driver_registration_form(chat_id, phone_number, first_name):
    """Send driver registration form as WebApp"""
    try:
        from url_utils import construct_url
        
        # Create registration form URL with user data
        webapp_url = construct_url(f'/driver-registration?phone={phone_number}&name={first_name}&telegram_id={chat_id}')
        
        message = f"🚚 *Driver Registration*\n\n"
        message += f"👋 Hello {first_name}!\n\n"
        message += f"📱 Phone: {phone_number}\n"
        message += f"🆔 Telegram ID: {chat_id}\n\n"
        message += f"📋 **Complete your driver registration using the form below:**\n\n"
        message += f"✅ Personal information\n"
        message += f"🚗 Vehicle details\n"
        message += f"📄 Document upload\n"
        message += f"📍 Location preferences\n\n"
        message += f"⏰ Registration takes 2-3 minutes to complete."
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📝 Complete Registration",
                        "web_app": {"url": webapp_url}
                    }
                ],
                [
                    {
                        "text": "📞 Contact Admin Instead",
                        "callback_data": "contact_admin"
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error sending registration form: {e}")
        # Fallback to admin contact message
        notify_admin_new_driver_attempt(chat_id, phone_number, first_name)
        
        message = f"👋 Hello {first_name}!\n\n"
        message += f"📱 Phone: {phone_number}\n"
        message += f"🚫 Registration system temporarily unavailable.\n\n"
        message += f"🎯 Your contact details have been sent to admin for manual registration.\n"
        message += f"⏳ Please wait for approval to start receiving orders.\n\n"
        message += f"📞 Contact admin if you have questions."
        
        send_driver_message(chat_id, message)

def send_driver_contact_request(chat_id):
    """Request contact sharing for automatic driver registration - iOS Compatible"""
    message = f"🚚 *Welcome to ET-FOOD Driver Bot!*\n\n"
    message += f"To get started, I need to verify your identity and link your Telegram account to your driver profile.\n\n"
    message += f"📞 **Please share your phone number** so I can:\n"
    message += f"✅ Find your driver profile in our system\n"
    message += f"✅ Automatically update your Telegram ID\n"
    message += f"✅ Activate your driver account\n\n"
    message += f"🔒 Your phone number will be used only for account verification and order notifications.\n\n"
    
    # iOS-compatible approach: Multiple options
    message += f"**Option 1 (Recommended):** Click the button below to share your contact\n"
    message += f"**Option 2 (iOS Alternative):** Type your phone number in format: +251912345678\n"
    message += f"**Option 3:** Contact admin for manual registration\n\n"
    message += f"👇 Try the button first:"
    
    keyboard = {
        "keyboard": [
            [
                {
                    "text": "📞 Share Phone Number",
                    "request_contact": True
                }
            ],
            [
                {
                    "text": "✍️ Type Phone Number Instead"
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_driver_registration_options(chat_id):
    """Send enhanced driver registration options with admin approval system"""
    message = f"🚗 *Welcome to ET-FOOD Driver Bot*\n\n"
    message += f"✅ *Registration successful!*\n\n"
    message += f"📋 **Next Steps:**\n"
    message += f"• Admin will review your application\n"
    message += f"• You'll receive approval notification here\n"
    message += f"• Share your location when approved\n"
    message += f"• Start receiving delivery orders\n\n"
    message += f"🔗 **Already approved?** Link your account to start receiving orders!"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🔗 Link Existing Account",
                    "callback_data": "link_account"
                }
            ],
            [
                {
                    "text": "📱 Driver Status",
                    "callback_data": "driver_status"
                },
                {
                    "text": "📞 Contact Admin",
                    "callback_data": "contact_support"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def handle_start_registration(chat_id):
    """Handle start registration callback"""
    try:
        from url_utils import get_base_url
        base_url = get_base_url()
        registration_url = f"{base_url}/driver-registration/{chat_id}"
        
        message = f"📝 *Driver Registration*\n\n"
        message += f"To complete your registration, please:\n\n"
        message += f"1️⃣ Click the registration link below\n"
        message += f"2️⃣ Fill out the application form\n"
        message += f"3️⃣ Upload required documents\n"
        message += f"4️⃣ Submit for admin approval\n\n"
        message += f"💡 **The registration form will open in your browser**\n\n"
        message += f"📄 **Required Documents:**\n"
        message += f"• Driver's License (Front & Back)\n"
        message += f"• Government ID (Front & Back)\n"
        message += f"• Vehicle Registration\n\n"
        message += f"🔗 **Registration Link:**\n{registration_url}\n\n"
        message += f"⚠️ **Note:** Keep this chat open during registration for updates."
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📝 Open Registration Form",
                        "url": registration_url
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
        
    except Exception as e:
        logger.error(f"Error handling start registration: {e}")
        send_driver_message(chat_id, "❌ Error starting registration. Please try again or contact support.")

def handle_link_account(chat_id):
    """Handle link existing account callback"""
    message = f"📞 *Link Existing Driver Account*\n\n"
    message += f"If you already have a driver account with ET-FOOD, please share your phone number to link your Telegram account.\n\n"
    message += f"👇 **Choose your option:**"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📞 Share Phone Number",
                    "callback_data": "share_contact_for_registration"
                }
            ],
            [
                {
                    "text": "✍️ Type Phone Number",
                    "callback_data": "type_phone_number"
                }
            ],
            [
                {
                    "text": "🔙 Back to Registration",
                    "callback_data": "back_to_registration"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_driver_welcome_message(chat_id, driver=None):
    """Enhanced BeU delivery-style driver welcome message with live location requirement"""
    if driver and driver.approval_status == 'approved':
        # Check location sharing status
        from datetime import datetime, timedelta
        location_active = False
        if driver.last_location_update:
            time_diff = datetime.utcnow() - driver.last_location_update
            location_active = time_diff.total_seconds() < 600  # Less than 10 minutes
        
        # Approved driver welcome with mandatory location sharing
        message = f"🚚 *Welcome back, {driver.name}!*\n\n"
        message += f"✅ *Status: APPROVED DRIVER*\n"
        message += f"📞 Phone: {driver.phone_number}\n"
        message += f"🚗 Vehicle: {driver.vehicle_type}\n\n"
        
        # Location sharing status
        if location_active:
            message += f"📍 **Location Status: ACTIVE** ✅\n"
            message += f"🟢 You can receive order assignments\n\n"
        else:
            message += f"📍 **Location Status: INACTIVE** ❌\n"
            message += f"🔴 You MUST share live location to receive orders\n\n"
            message += f"⚠️ **IMPORTANT**: Like BeU delivery system, you must share your live location to receive nearby orders!\n\n"
        
        # Create WebApp URL for driver panel using centralized utility
        from url_utils import construct_url
        webapp_url = construct_url(f'/driver-panel?driver_id={chat_id}')
        
        if location_active:
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
                            "text": "🔄 Toggle Online/Offline",
                            "callback_data": "toggle_status"
                        },
                        {
                            "text": "📊 View Status",
                            "callback_data": "driver_status"
                        }
                    ],
                    [
                        {
                            "text": "📍 Update Location",
                            "callback_data": "request_location"
                        },
                        {
                            "text": "📞 Support",
                            "callback_data": "contact_support"
                        }
                    ]
                ]
            }
        else:
            # Force location sharing first
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📍 SHARE LIVE LOCATION (Required)",
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
                            "text": "📞 Contact Support",
                            "callback_data": "contact_support"
                        }
                    ]
                ]
            }
    elif driver and driver.approval_status == 'pending':
        # Pending approval
        message = f"⏳ *Registration Under Review*\n\n"
        message += f"📝 Driver: {driver.name}\n"
        message += f"📞 Phone: {driver.phone_number}\n"
        message += f"🚗 Vehicle: {driver.vehicle_type}\n\n"
        message += f"📋 Your registration is being reviewed by our admin team.\n"
        message += f"⏰ Please wait for approval. You'll receive a notification once approved.\n\n"
        message += f"📞 Contact support if you have any questions."
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📞 Contact Support",
                        "callback_data": "contact_support"
                    }
                ]
            ]
        }
    elif driver and driver.approval_status == 'rejected':
        # Rejected driver
        message = f"❌ *Registration Rejected*\n\n"
        message += f"Unfortunately, your driver registration was not approved.\n"
        message += f"Reason: {driver.rejection_reason or 'Not specified'}\n\n"
        message += f"📱 You can register again with corrected information:"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🔄 Register Again",
                        "callback_data": "start_registration"
                    }
                ]
            ]
        }
    else:
        # New driver registration
        message = f"🚚 *Welcome to ET-FOOD Driver Bot!*\n\n"
        message += f"🔹 Join our delivery team and start earning!\n"
        message += f"🔹 Fast registration process\n"
        message += f"🔹 Flexible working hours\n"
        message += f"🔹 Competitive earnings\n\n"
        message += f"📱 Ready to become a driver? Start your registration:"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🚀 Driver Registration",
                        "callback_data": "start_registration"
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
        
        # Add action buttons
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📍 Share Location Now",
                        "callback_data": "request_location"
                    },
                    {
                        "text": "🔄 Toggle Status",
                        "callback_data": "toggle_availability"
                    }
                ],
                [
                    {
                        "text": "📱 View Orders",
                        "callback_data": "driver_orders"
                    },
                    {
                        "text": "💰 View Earnings",
                        "callback_data": "driver_earnings"
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
        
    except Exception as e:
        logger.error(f"Error getting driver status: {e}")
        send_driver_message(chat_id, "❌ Error retrieving status. Please try again later.")

def send_driver_help_message(chat_id):
    """Send help message to driver"""
    message = """🚚 *ET-FOOD Driver Bot Help*

**📱 Interactive Commands:**
All commands now have easy-to-use buttons:
• Status & Profile Information
• Location Sharing & Updates
• Active Orders & Deliveries
• Availability Toggle (Online/Offline)
• Earnings Summary & Stats
• Real-time Order Notifications

**🎯 Key Features:**
• Real-time order notifications with 1-minute timer
• GPS-based order assignment within 10km radius
• Live location tracking (like BeU delivery)
• Direct customer/restaurant contact buttons
• Comprehensive earnings tracking
• Performance analytics dashboard

**📍 Location Sharing (REQUIRED):**
Like BeU delivery, you MUST share live location to receive orders. The system finds the 3 nearest available drivers and notifies them instantly.

**💡 Pro Tips:**
• Keep location sharing active during your shift
• Accept orders quickly (60-second countdown)
• Use inline buttons for faster navigation
• Contact support for any issues

**🚀 Getting Started:**
1. Share your location using the button below
2. Toggle your status to "Available"
3. Wait for order notifications
4. Accept orders and start earning!

Need help? Use the Support button below."""
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Share Location",
                    "callback_data": "request_location"
                },
                {
                    "text": "📊 Check Status",
                    "callback_data": "driver_status"
                }
            ],
            [
                {
                    "text": "📱 View Orders",
                    "callback_data": "driver_orders"
                },
                {
                    "text": "🔄 Toggle Status",
                    "callback_data": "toggle_availability"
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
                message = "📋 No active orders at the moment.\n\nYou'll be notified when new orders are available!"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📍 Share Location",
                                "callback_data": "request_location"
                            },
                            {
                                "text": "🔄 Toggle Status",
                                "callback_data": "toggle_availability"
                            }
                        ],
                        [
                            {
                                "text": "📊 Check Status",
                                "callback_data": "driver_status"
                            }
                        ]
                    ]
                }
                
                send_driver_message(chat_id, message, keyboard=keyboard)
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
            
            # Add action buttons for order management
            from url_utils import construct_url
            webapp_url = construct_url(f'/driver-panel?driver_id={driver.id}')
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
                            "text": "📍 Share Location",
                            "callback_data": "request_location"
                        },
                        {
                            "text": "📊 Check Status",
                            "callback_data": "driver_status"
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
    """Send driver earnings summary with detailed breakdown and inline buttons"""
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
            
            # Add action buttons
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📱 View Orders",
                            "callback_data": "driver_orders"
                        },
                        {
                            "text": "📊 Check Status",
                            "callback_data": "driver_status"
                        }
                    ],
                    [
                        {
                            "text": "🔄 Toggle Availability",
                            "callback_data": "toggle_availability"
                        },
                        {
                            "text": "📍 Share Location",
                            "callback_data": "request_location"
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
            
    except Exception as e:
        logger.error(f"Error getting driver earnings: {e}")
        send_driver_message(chat_id, "❌ Error retrieving earnings. Please try again later.")

def send_driver_help_message_old(chat_id):
    """Legacy help message - replaced by comprehensive inline button version"""
    # This function is kept for compatibility but redirects to the new one
    send_driver_help_message(chat_id)

def set_driver_webhook():
    """Set webhook for driver bot with retry mechanism"""
    import time
    from url_utils import construct_webhook_url
    
    # Use the centralized URL construction logic
    webhook_url = construct_webhook_url('driver-webhook')
    
    if not webhook_url or 'localhost' in webhook_url:
        logger.error("No valid webhook domain available (REPLIT_DEV_DOMAIN or RENDER_EXTERNAL_URL)")
        return False
    
    url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/setWebhook"
    
    data = {
        'url': webhook_url,
        'allowed_updates': ['message', 'callback_query']
    }
    
    # Add delay and retry mechanism for host resolution
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Add delay before webhook setup to allow host resolution
            if attempt > 0:
                logger.info(f"Retrying driver webhook setup (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info(f"Driver bot webhook set successfully: {webhook_url}")
                return True
            else:
                logger.warning(f"Failed to set driver webhook (attempt {attempt + 1}): {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error setting driver webhook (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to set driver webhook after {max_retries} attempts: {e}")
        except Exception as e:
            logger.error(f"Unexpected error setting driver webhook: {e}")
            break
    
    return False

# Integration function for main system
def handle_manual_phone_input(chat_id, phone_text):
    """Handle manually typed phone numbers for iOS compatibility"""
    try:
        # Clean and validate phone number
        clean_phone = phone_text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Handle different formats
        if clean_phone.startswith('09'):
            # Ethiopian local format, add country code
            clean_phone = '+251' + clean_phone[1:]
        elif clean_phone.startswith('251'):
            # Missing + sign
            clean_phone = '+' + clean_phone
        elif not clean_phone.startswith('+251'):
            # Invalid format
            message = "❌ *Invalid Phone Number Format*\n\n"
            message += "Please use one of these formats:\n"
            message += "• +251912345678\n"
            message += "• 251912345678\n"
            message += "• 0912345678\n\n"
            message += "Try again:"
            
            send_driver_message(chat_id, message)
            return False
        
        # Validate length (Ethiopian numbers are typically 13 characters with +251)
        if len(clean_phone) != 13:
            message = "❌ *Invalid Phone Number Length*\n\n"
            message += f"Your number: {clean_phone}\n"
            message += "Expected format: +251912345678 (13 digits)\n\n"
            message += "Please try again:"
            
            send_driver_message(chat_id, message)
            return False
        
        # Create mock contact data for processing
        contact_data = {
            'phone_number': clean_phone,
            'first_name': 'Driver',  # Default name, will be updated during registration
            'last_name': ''
        }
        
        # Process as regular contact sharing
        handle_driver_contact_share(chat_id, contact_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling manual phone input: {e}")
        send_driver_message(chat_id, "❌ Error processing phone number. Please try again or contact support.")
        return False

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
def send_driver_registration_notification(chat_id, driver_name, phone_number):
    """Send notification to driver about successful registration"""
    message = f"🎉 *Registration Successful!*\n\n"
    message += f"✅ You have been successfully registered as a driver for ET-FOOD!\n\n"
    message += f"👤 **Driver Details:**\n"
    message += f"📛 Name: {driver_name}\n"
    message += f"📞 Phone: {phone_number}\n\n"
    message += f"🚀 **Next Steps:**\n"
    message += f"1️⃣ Share your location to start receiving orders\n"
    message += f"2️⃣ Keep your status as \"Available\" when ready to deliver\n"
    message += f"3️⃣ Use buttons below to manage your driver account\n\n"
    message += f"📍 **Location Sharing Required:**\n"
    message += f"• Share your location to receive nearby orders\n"
    message += f"• Location updates are needed every 10 minutes\n"
    message += f"• This helps us assign you the closest deliveries\n\n"
    message += f"💰 Start earning by sharing your location now!"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Share My Location",
                    "callback_data": "request_location"
                }
            ],
            [
                {
                    "text": "📊 Check Status",
                    "callback_data": "driver_status"
                },
                {
                    "text": "📱 View Orders",
                    "callback_data": "driver_orders"
                }
            ],
            [
                {
                    "text": "🔄 Toggle Availability",
                    "callback_data": "toggle_availability"
                },
                {
                    "text": "💰 View Earnings",
                    "callback_data": "driver_earnings"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

