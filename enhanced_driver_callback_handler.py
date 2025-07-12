"""
Enhanced Driver Bot Callback Handler
Handles all driver bot callback queries including order acceptance, location sharing, and real-time delivery workflow
"""

import logging
import json
from datetime import datetime
from driver_bot import send_driver_message, answer_callback_query
from real_time_delivery_system import delivery_system
from models import Driver, Order, AdminUser
from extensions import db
from bot_minimal import send_message, send_message_to_admin

logger = logging.getLogger(__name__)

def is_registered_driver(chat_id):
    """Check if user is a registered and approved driver"""
    try:
        from app import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            return driver and driver.is_approved
    except Exception as e:
        logger.error(f"Error checking driver registration: {e}")
        return False

def handle_unregistered_user(chat_id, callback_query_id):
    """Handle callbacks from unregistered users"""
    try:
        answer_callback_query(callback_query_id, "❌ Please contact admin to register as driver")
        
        message = f"❌ *Access Denied*\n\n"
        message += f"This feature is only available for registered drivers.\n\n"
        message += f"📞 Contact admin to register as a delivery driver."
        
        send_driver_message(chat_id, message)
        
    except Exception as e:
        logger.error(f"Error handling unregistered user: {e}")

def handle_driver_callback(callback_query):
    """Handle all driver bot callback queries"""
    try:
        callback_data = callback_query.get('data', '')
        chat_id = callback_query['from']['id']
        callback_query_id = callback_query['id']
        
        logger.info(f"Received callback from driver {chat_id}: {callback_data}")
        
        # Order acceptance/rejection
        if callback_data.startswith('driver_accept_'):
            order_id = int(callback_data.split('_')[2])
            handle_order_acceptance(chat_id, order_id, callback_query_id)
            
        elif callback_data.startswith('driver_decline_'):
            order_id = int(callback_data.split('_')[2])
            handle_order_rejection(chat_id, order_id, callback_query_id)
            
        # Legacy support for accept_order_ format
        elif callback_data.startswith('accept_order_'):
            order_id = int(callback_data.split('_')[2])
            handle_order_acceptance(chat_id, order_id, callback_query_id)
            
        elif callback_data.startswith('decline_order_'):
            order_id = int(callback_data.split('_')[2])
            handle_order_rejection(chat_id, order_id, callback_query_id)
            
        # Location sharing
        elif callback_data == 'request_location':
            handle_location_request(chat_id, callback_query_id)
            
        elif callback_data == 'enable_live_location':
            handle_enable_live_location(chat_id, callback_query_id)
            
        # Order management
        elif callback_data.startswith('pickup_complete_'):
            order_id = int(callback_data.split('_')[2])
            handle_pickup_complete(chat_id, order_id, callback_query_id)
            
        elif callback_data.startswith('delivery_complete_'):
            order_id = int(callback_data.split('_')[2])
            handle_delivery_complete(chat_id, order_id, callback_query_id)
            
        # Customer contact
        elif callback_data.startswith('call_customer_'):
            order_id = int(callback_data.split('_')[2])
            handle_call_customer(chat_id, order_id, callback_query_id)
            
        elif callback_data.startswith('navigate_customer_'):
            order_id = int(callback_data.split('_')[2])
            handle_navigate_customer(chat_id, order_id, callback_query_id)
            
        # Restaurant contact
        elif callback_data == 'call_restaurant':
            handle_call_restaurant(chat_id, callback_query_id)
            
        elif callback_data == 'navigate_restaurant':
            handle_navigate_restaurant(chat_id, callback_query_id)
            
        # Driver status management (only for registered drivers)
        elif callback_data == 'driver_status':
            if is_registered_driver(chat_id):
                handle_driver_status(chat_id, callback_query_id)
            else:
                handle_unregistered_user(chat_id, callback_query_id)
            
        elif callback_data == 'driver_orders':
            if is_registered_driver(chat_id):
                handle_driver_orders(chat_id, callback_query_id)
            else:
                handle_unregistered_user(chat_id, callback_query_id)
            
        elif callback_data == 'toggle_availability':
            handle_toggle_availability(chat_id, callback_query_id)
            
        elif callback_data == 'driver_earnings':
            handle_driver_earnings(chat_id, callback_query_id)
            
        elif callback_data == 'driver_help':
            handle_driver_help(chat_id, callback_query_id)
            
        elif callback_data == 'contact_support':
            handle_contact_support(chat_id, callback_query_id)
            
        else:
            answer_callback_query(callback_query_id, "Unknown action")
            
    except Exception as e:
        logger.error(f"Error handling driver callback: {e}")
        answer_callback_query(callback_query_id, "Error processing request")

def handle_order_acceptance(chat_id, order_id, callback_query_id):
    """Handle order acceptance by driver"""
    try:
        from app import app
        from driver_bot import handle_order_acceptance as driver_handle_order_acceptance
        
        with app.app_context():
            # Use the driver bot function to handle order acceptance
            success = driver_handle_order_acceptance(chat_id, order_id, None)
            
            if success:
                answer_callback_query(callback_query_id, "✅ Order accepted successfully!")
                logger.info(f"Order {order_id} successfully accepted by driver {chat_id}")
            else:
                answer_callback_query(callback_query_id, "❌ Order no longer available")
                logger.warning(f"Order {order_id} could not be accepted by driver {chat_id}")
                
    except Exception as e:
        logger.error(f"Error handling order acceptance: {e}")
        answer_callback_query(callback_query_id, "❌ Error accepting order")

def handle_order_rejection(chat_id, order_id, callback_query_id):
    """Handle order rejection by driver"""
    try:
        from app import app
        from driver_bot import handle_order_rejection as driver_handle_order_rejection
        
        with app.app_context():
            # Use the driver bot function to handle order rejection
            success = driver_handle_order_rejection(chat_id, order_id, None)
            
            if success:
                answer_callback_query(callback_query_id, "Order declined")
                logger.info(f"Order {order_id} declined by driver {chat_id}")
            else:
                answer_callback_query(callback_query_id, "❌ Order already processed")
                logger.warning(f"Order {order_id} could not be declined by driver {chat_id}")
                
    except Exception as e:
        logger.error(f"Error handling order rejection: {e}")
        answer_callback_query(callback_query_id, "❌ Error declining order")

def handle_location_request(chat_id, callback_query_id):
    """Handle location sharing request"""
    try:
        message = f"📍 *Share Your Live Location*\n\n"
        message += f"🚚 **Real-time tracking required**\n\n"
        message += f"📱 **How to share:**\n"
        message += f"1. Tap attachment button (📎)\n"
        message += f"2. Select 'Location'\n"
        message += f"3. Choose 'Share Live Location'\n"
        message += f"4. Select duration (30 min recommended)\n"
        message += f"5. Tap 'Send'\n\n"
        message += f"⚠️ **Important:** Keep location sharing active during delivery!"
        
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
        
        send_driver_message(chat_id, message, keyboard=keyboard)
        answer_callback_query(callback_query_id, "Location sharing guide sent")
        
    except Exception as e:
        logger.error(f"Error handling location request: {e}")
        answer_callback_query(callback_query_id, "Error requesting location")

def handle_enable_live_location(chat_id, callback_query_id):
    """Handle enabling live location sharing"""
    try:
        message = f"🔄 *Enable Live Location Sharing*\n\n"
        message += f"📍 To enable automatic location updates:\n\n"
        message += f"**For Android:**\n"
        message += f"1. Open attachment menu\n"
        message += f"2. Select 'Location'\n"
        message += f"3. Choose 'Share Live Location'\n"
        message += f"4. Select 30 minutes\n\n"
        message += f"**For iOS:**\n"
        message += f"1. Tap '+' button\n"
        message += f"2. Select 'Location'\n"
        message += f"3. Choose 'Share Live Location'\n"
        message += f"4. Select duration\n\n"
        message += f"⚠️ This ensures customers can track your delivery progress!"
        
        send_driver_message(chat_id, message)
        answer_callback_query(callback_query_id, "Live location instructions sent")
        
    except Exception as e:
        logger.error(f"Error handling enable live location: {e}")
        answer_callback_query(callback_query_id, "Error enabling live location")

def handle_pickup_complete(chat_id, order_id, callback_query_id):
    """Handle pickup completion"""
    try:
        from app import app
        
        with app.app_context():
            order = db.session.get(Order, order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                answer_callback_query(callback_query_id, "Order or driver not found")
                return
            
            # Update order status
            order.status = 'out_for_delivery'
            order.pickup_time = datetime.utcnow()
            db.session.commit()
            
            # Notify driver
            message = f"✅ *Pickup Confirmed*\n\n"
            message += f"📋 Order #{order_id}\n"
            message += f"🚚 Status: Out for delivery\n"
            message += f"📍 Navigate to customer location\n\n"
            message += f"👤 **Customer:** {order.customer_name}\n"
            message += f"📞 **Phone:** {order.customer_phone}\n"
            message += f"📍 **Address:** {order.customer_address}\n\n"
            message += f"🎯 **Next Steps:**\n"
            message += f"• Share live location for tracking\n"
            message += f"• Navigate to customer\n"
            message += f"• Complete delivery"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order_id}"
                        },
                        {
                            "text": "🗺️ Navigate",
                            "callback_data": f"navigate_customer_{order_id}"
                        }
                    ],
                    [
                        {
                            "text": "📍 Share Location",
                            "callback_data": "request_location"
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
            
            # Notify customer
            customer_message = f"🚚 *Order Picked Up!*\n\n"
            customer_message += f"📋 Order #{order_id}\n"
            customer_message += f"🚗 Driver: {driver.name}\n"
            customer_message += f"📞 Phone: {driver.phone_number}\n\n"
            customer_message += f"🕐 Your order is on the way!\n"
            customer_message += f"📍 You can track the driver's location in real-time."
            
            send_message(order.telegram_user_id, customer_message)
            
            # Notify admin
            admin_message = f"🚚 *Pickup Complete*\n\n"
            admin_message += f"📋 Order #{order_id}\n"
            admin_message += f"🚗 Driver: {driver.name}\n"
            admin_message += f"👤 Customer: {order.customer_name}\n"
            admin_message += f"📍 Status: Out for delivery"
            
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, admin_message)
            
            answer_callback_query(callback_query_id, "✅ Pickup confirmed!")
            
    except Exception as e:
        logger.error(f"Error handling pickup completion: {e}")
        answer_callback_query(callback_query_id, "Error confirming pickup")

def handle_delivery_complete(chat_id, order_id, callback_query_id):
    """Handle delivery completion"""
    try:
        from app import app
        
        with app.app_context():
            order = db.session.get(Order, order_id)
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not order or not driver:
                answer_callback_query(callback_query_id, "Order or driver not found")
                return
            
            # Update order status
            order.status = 'delivered'
            order.delivery_time = datetime.utcnow()
            
            # Make driver available again
            driver.is_available = True
            
            db.session.commit()
            
            # Calculate delivery time
            delivery_duration = ""
            if hasattr(order, 'pickup_time') and order.pickup_time:
                duration = order.delivery_time - order.pickup_time
                minutes = int(duration.total_seconds() / 60)
                delivery_duration = f"{minutes} minutes"
            
            # Notify driver with customer rating info
            message = f"🎉 *Delivery Completed Successfully!*\n\n"
            message += f"📋 Order #{order_id}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"💰 Amount: {order.total_amount:.2f} ETB\n"
            if delivery_duration:
                message += f"⏱️ Delivery time: {delivery_duration}\n"
            message += f"\n⭐ **Customer is rating this delivery**\n"
            message += f"✅ **Status:** Automatically available for new orders\n"
            message += f"💪 Great job! You're ready for your next delivery!"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📊 View Earnings",
                            "callback_data": "driver_earnings"
                        },
                        {
                            "text": "🔄 Check Status",
                            "callback_data": "driver_status"
                        }
                    ],
                    [
                        {
                            "text": "📍 Share Location",
                            "callback_data": "request_location"
                        },
                        {
                            "text": "📋 View Orders",
                            "callback_data": "driver_orders"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            
            # Notify customer with rating options
            customer_message = f"🎉 *Delivery Completed!*\n\n"
            customer_message += f"📋 Order #{order_id}\n"
            customer_message += f"🚗 Driver: {driver.name}\n"
            customer_message += f"⏱️ Delivered in: {delivery_duration}\n\n"
            customer_message += f"✅ Your order has been delivered successfully!\n"
            customer_message += f"🌟 How was your delivery experience?"
            
            rating_keyboard = {
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
                    ]
                ]
            }
            
            send_message(order.telegram_user_id, customer_message, keyboard=rating_keyboard)
            
            # Notify admin
            admin_message = f"✅ *Delivery Completed*\n\n"
            admin_message += f"📋 Order #{order_id}\n"
            admin_message += f"🚗 Driver: {driver.name}\n"
            admin_message += f"👤 Customer: {order.customer_name}\n"
            admin_message += f"💰 Amount: {order.total_amount:.2f} ETB\n"
            admin_message += f"⏱️ Delivery time: {delivery_duration}\n\n"
            admin_message += f"🎉 Order delivered successfully!"
            
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, admin_message)
            
            answer_callback_query(callback_query_id, "🎉 Delivery completed!")
            
    except Exception as e:
        logger.error(f"Error handling delivery completion: {e}")
        answer_callback_query(callback_query_id, "Error completing delivery")

def handle_call_customer(chat_id, order_id, callback_query_id):
    """Handle customer calling"""
    try:
        from app import app
        
        with app.app_context():
            order = db.session.get(Order, order_id)
            
            if not order:
                answer_callback_query(callback_query_id, "Order not found")
                return
            
            message = f"📞 *Customer Contact*\n\n"
            message += f"👤 **Customer:** {order.customer_name}\n"
            message += f"📞 **Phone:** {order.customer_phone}\n"
            message += f"📍 **Address:** {order.customer_address}\n\n"
            message += f"💰 **Order Total:** {order.total_amount:.2f} ETB\n"
            message += f"💳 **Payment Method:** {order.payment_method}\n\n"
            message += f"📞 Tap the button below to call the customer:"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "url": f"tel:{order.customer_phone}"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            answer_callback_query(callback_query_id, "Customer contact info sent")
            
    except Exception as e:
        logger.error(f"Error handling customer call: {e}")
        answer_callback_query(callback_query_id, "Error getting customer info")

def handle_navigate_customer(chat_id, order_id, callback_query_id):
    """Handle customer navigation"""
    try:
        from app import app
        
        with app.app_context():
            order = db.session.get(Order, order_id)
            
            if not order:
                answer_callback_query(callback_query_id, "Order not found")
                return
            
            # Use GPS coordinates if available, otherwise use address
            if order.location_lat and order.location_lng:
                maps_url = f"https://maps.google.com/?q={order.location_lat},{order.location_lng}"
                waze_url = f"https://waze.com/ul?ll={order.location_lat},{order.location_lng}"
            else:
                # Use address for navigation
                address = order.customer_address.replace(' ', '+')
                maps_url = f"https://maps.google.com/?q={address}"
                waze_url = f"https://waze.com/ul?q={address}"
            
            message = f"🗺️ *Navigate to Customer*\n\n"
            message += f"👤 **Customer:** {order.customer_name}\n"
            message += f"📍 **Address:** {order.customer_address}\n"
            if order.location_lat and order.location_lng:
                message += f"📍 **GPS:** {order.location_lat}, {order.location_lng}\n"
            message += f"\n🚗 Choose your preferred navigation app:"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🗺️ Google Maps",
                            "url": maps_url
                        },
                        {
                            "text": "🚗 Waze",
                            "url": waze_url
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            answer_callback_query(callback_query_id, "Navigation options sent")
            
    except Exception as e:
        logger.error(f"Error handling customer navigation: {e}")
        answer_callback_query(callback_query_id, "Error getting navigation")

def handle_call_restaurant(chat_id, callback_query_id):
    """Handle restaurant calling"""
    try:
        # ET-FOOD restaurant contact info
        restaurant_phone = "+251911234567"  # Replace with actual restaurant number
        restaurant_name = "ET-FOOD Kitchen"
        
        message = f"🏪 *Restaurant Contact*\n\n"
        message += f"🏪 **Restaurant:** {restaurant_name}\n"
        message += f"📞 **Phone:** {restaurant_phone}\n"
        message += f"📍 **Address:** Addis Ababa, Ethiopia\n\n"
        message += f"📞 Tap the button below to call the restaurant:"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📞 Call Restaurant",
                        "url": f"tel:{restaurant_phone}"
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard)
        answer_callback_query(callback_query_id, "Restaurant contact info sent")
        
    except Exception as e:
        logger.error(f"Error handling restaurant call: {e}")
        answer_callback_query(callback_query_id, "Error getting restaurant info")

def handle_navigate_restaurant(chat_id, callback_query_id):
    """Handle restaurant navigation"""
    try:
        # ET-FOOD restaurant location (replace with actual coordinates)
        restaurant_lat = 9.047658
        restaurant_lng = 38.741143
        restaurant_address = "ET-FOOD Kitchen, Addis Ababa"
        
        maps_url = f"https://maps.google.com/?q={restaurant_lat},{restaurant_lng}"
        waze_url = f"https://waze.com/ul?ll={restaurant_lat},{restaurant_lng}"
        
        message = f"🗺️ *Navigate to Restaurant*\n\n"
        message += f"🏪 **Restaurant:** ET-FOOD Kitchen\n"
        message += f"📍 **Address:** {restaurant_address}\n"
        message += f"📍 **GPS:** {restaurant_lat}, {restaurant_lng}\n\n"
        message += f"🚗 Choose your preferred navigation app:"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🗺️ Google Maps",
                        "url": maps_url
                    },
                    {
                        "text": "🚗 Waze",
                        "url": waze_url
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard)
        answer_callback_query(callback_query_id, "Restaurant navigation sent")
        
    except Exception as e:
        logger.error(f"Error handling restaurant navigation: {e}")
        answer_callback_query(callback_query_id, "Error getting navigation")

def handle_driver_status(chat_id, callback_query_id):
    """Handle driver status request"""
    try:
        from app import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not driver:
                answer_callback_query(callback_query_id, "Driver not found")
                return
            
            # Calculate location status
            location_status = "Inactive"
            if driver.last_location_update:
                from datetime import timedelta
                time_diff = datetime.utcnow() - driver.last_location_update
                if time_diff.total_seconds() < 600:  # Less than 10 minutes
                    location_status = "Active"
            
            message = f"📊 *Driver Status*\n\n"
            message += f"👤 **Name:** {driver.name}\n"
            message += f"📞 **Phone:** {driver.phone_number}\n"
            message += f"🚗 **Vehicle:** {driver.vehicle_type}\n\n"
            message += f"✅ **Approval:** {'Approved' if driver.is_approved else 'Pending'}\n"
            message += f"🟢 **Active:** {'Yes' if driver.is_active else 'No'}\n"
            message += f"📍 **Available:** {'Yes' if driver.is_available else 'No'}\n"
            message += f"📍 **Location:** {location_status}\n\n"
            
            if driver.last_location_update:
                message += f"🕐 **Last Update:** {driver.last_location_update.strftime('%H:%M %p')}\n"
            else:
                message += f"⚠️ **No location shared yet**\n"
            
            message += f"\n🎯 **Ready for orders:** {'Yes' if driver.is_approved and driver.is_active and driver.is_available else 'No'}"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🔄 Toggle Availability",
                            "callback_data": "toggle_availability"
                        },
                        {
                            "text": "📍 Share Location",
                            "callback_data": "request_location"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            answer_callback_query(callback_query_id, "Status updated")
            
    except Exception as e:
        logger.error(f"Error handling driver status: {e}")
        answer_callback_query(callback_query_id, "Error getting status")

def handle_driver_orders(chat_id, callback_query_id):
    """Handle driver orders request"""
    try:
        from app import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not driver:
                answer_callback_query(callback_query_id, "Driver not found")
                return
            
            # Get active orders for this driver
            active_orders = Order.query.filter_by(
                driver_id=driver.id,
                status='confirmed'
            ).all()
            
            if not active_orders:
                message = f"📋 *Current Orders*\n\n"
                message += f"🚫 No active orders assigned to you.\n\n"
                message += f"✅ You are available for new delivery assignments.\n"
                message += f"📍 Make sure your location is shared to receive orders."
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📍 Share Location",
                                "callback_data": "request_location"
                            }
                        ]
                    ]
                }
            else:
                message = f"📋 *Current Orders ({len(active_orders)})*\n\n"
                
                for order in active_orders:
                    message += f"**Order #{order.id}**\n"
                    message += f"👤 Customer: {order.customer_name}\n"
                    message += f"📞 Phone: {order.customer_phone}\n"
                    message += f"💰 Total: {order.total_amount:.2f} ETB\n"
                    message += f"📍 Status: {order.status.replace('_', ' ').title()}\n\n"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📍 Share Location",
                                "callback_data": "request_location"
                            }
                        ]
                    ]
                }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            answer_callback_query(callback_query_id, "Orders updated")
            
    except Exception as e:
        logger.error(f"Error handling driver orders: {e}")
        answer_callback_query(callback_query_id, "Error getting orders")

def handle_toggle_availability(chat_id, callback_query_id):
    """Handle availability toggle"""
    try:
        from app import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not driver:
                answer_callback_query(callback_query_id, "Driver not found")
                return
            
            # Toggle availability
            driver.is_available = not driver.is_available
            db.session.commit()
            
            status = "Available" if driver.is_available else "Unavailable"
            message = f"🔄 *Availability Updated*\n\n"
            message += f"📊 **New Status:** {status}\n\n"
            
            if driver.is_available:
                message += f"✅ You are now available for new orders.\n"
                message += f"📍 Make sure your location is shared to receive assignments."
            else:
                message += f"❌ You are now unavailable for new orders.\n"
                message += f"🔄 Toggle again when ready to receive orders."
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📍 Share Location",
                            "callback_data": "request_location"
                        },
                        {
                            "text": "📊 View Status",
                            "callback_data": "driver_status"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            answer_callback_query(callback_query_id, f"Status: {status}")
            
    except Exception as e:
        logger.error(f"Error toggling availability: {e}")
        answer_callback_query(callback_query_id, "Error toggling availability")

def handle_driver_earnings(chat_id, callback_query_id):
    """Handle driver earnings request"""
    try:
        from app import app
        
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=chat_id).first()
            
            if not driver:
                answer_callback_query(callback_query_id, "Driver not found")
                return
            
            # Calculate earnings from completed orders
            completed_orders = Order.query.filter_by(
                driver_id=driver.id,
                status='delivered'
            ).all()
            
            total_earnings = sum(order.total_amount * 0.15 for order in completed_orders)  # 15% commission
            total_deliveries = len(completed_orders)
            
            message = f"💰 *Earnings Summary*\n\n"
            message += f"👤 **Driver:** {driver.name}\n"
            message += f"📊 **Total Deliveries:** {total_deliveries}\n"
            message += f"💰 **Total Earnings:** {total_earnings:.2f} ETB\n"
            
            if total_deliveries > 0:
                avg_per_delivery = total_earnings / total_deliveries
                message += f"📈 **Average per Delivery:** {avg_per_delivery:.2f} ETB\n"
            
            message += f"\n🎯 **Commission Rate:** 15% of order value\n"
            message += f"💪 Keep up the great work!"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📊 View Status",
                            "callback_data": "driver_status"
                        },
                        {
                            "text": "🔄 Toggle Availability",
                            "callback_data": "toggle_availability"
                        }
                    ]
                ]
            }
            
            send_driver_message(chat_id, message, keyboard=keyboard)
            answer_callback_query(callback_query_id, "Earnings updated")
            
    except Exception as e:
        logger.error(f"Error handling driver earnings: {e}")
        answer_callback_query(callback_query_id, "Error getting earnings")

def handle_driver_help(chat_id, callback_query_id):
    """Handle driver help request"""
    try:
        message = f"❓ *ET-FOOD Driver Help*\n\n"
        message += f"🚚 **Available Commands:**\n"
        message += f"• 📊 View Status - Check your driver status\n"
        message += f"• 📋 Current Orders - See assigned orders\n"
        message += f"• 🔄 Toggle Availability - Go online/offline\n"
        message += f"• 💰 View Earnings - Check your earnings\n"
        message += f"• 📍 Share Location - Update your location\n\n"
        message += f"🎯 **How to receive orders:**\n"
        message += f"1. Make sure you're approved ✅\n"
        message += f"2. Share your live location 📍\n"
        message += f"3. Toggle availability to 'Available' 🟢\n"
        message += f"4. Wait for order notifications 📱\n\n"
        message += f"📞 **Support:** Contact admin for help\n"
        message += f"🚀 **Version:** ET-FOOD Driver Bot v2.0"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📊 View Status",
                        "callback_data": "driver_status"
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
        answer_callback_query(callback_query_id, "Help information sent")
        
    except Exception as e:
        logger.error(f"Error handling driver help: {e}")
        answer_callback_query(callback_query_id, "Error getting help")

def handle_contact_support(chat_id, callback_query_id):
    """Handle contact support request"""
    try:
        message = f"📞 *Contact Support*\n\n"
        message += f"🆘 **Need help?**\n\n"
        message += f"📱 **Admin Contact:**\n"
        message += f"• Telegram: @etfood_admin\n"
        message += f"• Phone: +251911234567\n"
        message += f"• Email: admin@etfood.com\n\n"
        message += f"🕐 **Support Hours:**\n"
        message += f"• Monday - Sunday: 24/7\n"
        message += f"• Response time: Within 30 minutes\n\n"
        message += f"📝 **Common Issues:**\n"
        message += f"• Can't receive orders: Check location sharing\n"
        message += f"• Account problems: Contact admin\n"
        message += f"• Technical issues: Restart the bot\n\n"
        message += f"🚀 We're here to help you succeed!"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📱 Contact Admin",
                        "url": "https://t.me/etfood_admin"
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard)
        answer_callback_query(callback_query_id, "Support info sent")
        
    except Exception as e:
        logger.error(f"Error handling contact support: {e}")
        answer_callback_query(callback_query_id, "Error getting support info")