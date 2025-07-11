"""
Enhanced Driver System with Real-time Delivery Workflow
Handles driver linking, approval notifications, and complete delivery process
"""

import logging
from datetime import datetime
from models import Driver, Order, AdminUser
from extensions import db
from app import app
from driver_bot import send_driver_message, send_driver_welcome_message
from admin_approval_system import notify_admin_new_driver_registration

logger = logging.getLogger(__name__)

def fix_driver_telegram_linking():
    """Fix drivers with missing Telegram account links"""
    try:
        with app.app_context():
            # Get all drivers without Telegram IDs
            unlinked_drivers = Driver.query.filter(
                (Driver.telegram_user_id == None) | (Driver.telegram_user_id == '')
            ).all()
            
            logger.info(f"Found {len(unlinked_drivers)} drivers without Telegram links")
            
            for driver in unlinked_drivers:
                # Create admin notification about unlinked driver
                notify_admin_unlinked_driver(driver)
                
    except Exception as e:
        logger.error(f"Error fixing driver Telegram linking: {e}")

def notify_admin_unlinked_driver(driver):
    """Notify admin about driver without Telegram link"""
    try:
        admins = AdminUser.query.filter_by(is_active=True).all()
        
        message = f"⚠️ *Driver Account Needs Linking*\n\n"
        message += f"👤 Driver: {driver.name}\n"
        message += f"📱 Phone: {driver.phone_number}\n"
        message += f"🆔 Telegram ID: Not linked\n\n"
        message += f"❌ **Issue**: Driver cannot receive order notifications\n\n"
        message += f"🔧 **Solution**: Driver needs to:\n"
        message += f"1. Start @Food_Driver_Bot\n"
        message += f"2. Share their contact to link account\n"
        message += f"3. System will automatically link their profile\n\n"
        message += f"📞 Contact driver: {driver.phone_number}"
        
        for admin in admins:
            from bot_minimal import send_message_to_admin
            send_message_to_admin(admin.telegram_user_id, message)
            
    except Exception as e:
        logger.error(f"Error notifying admin about unlinked driver: {e}")

def send_driver_approval_success_message(driver_id):
    """Send approval success message to driver"""
    try:
        with app.app_context():
            driver = Driver.query.get(driver_id)
            if not driver or not driver.telegram_user_id:
                logger.warning(f"Driver {driver_id} not found or no Telegram ID")
                return False
            
            # Send comprehensive approval message
            message = f"🎉 *Congratulations! Your Driver Application is APPROVED!*\n\n"
            message += f"✅ **Status**: Active Driver\n"
            message += f"👤 **Name**: {driver.name}\n"
            message += f"🚗 **Vehicle**: {driver.vehicle_type or 'Not specified'}\n"
            message += f"📱 **Phone**: {driver.phone_number}\n\n"
            message += f"🎯 **You can now receive delivery orders!**\n\n"
            message += f"📍 **Important**: Share your location to start receiving orders\n"
            message += f"🕐 **Working Hours**: Available 24/7\n"
            message += f"💰 **Earnings**: Track your daily earnings\n\n"
            message += f"🔥 **Get started immediately:**"
            
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
                            "text": "📊 View Driver Status",
                            "callback_data": "driver_status"
                        },
                        {
                            "text": "💰 View Earnings",
                            "callback_data": "driver_earnings"
                        }
                    ],
                    [
                        {
                            "text": "📋 View Orders",
                            "callback_data": "driver_orders"
                        },
                        {
                            "text": "❓ Help",
                            "callback_data": "driver_help"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver.telegram_user_id, message, keyboard=keyboard)
            
            # Send welcome message with full instructions
            send_driver_welcome_message(driver.telegram_user_id, driver)
            
            logger.info(f"Sent approval success message to driver {driver.name}")
            return True
            
    except Exception as e:
        logger.error(f"Error sending approval success message: {e}")
        return False

def handle_order_acceptance_workflow(driver_telegram_id, order_id):
    """Complete workflow when driver accepts order"""
    try:
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
            order = Order.query.get(order_id)
            
            if not driver or not order:
                logger.error(f"Driver or order not found for acceptance workflow")
                return False
            
            # Update order status
            order.status = 'confirmed'
            order.driver_id = driver.id
            order.updated_at = datetime.utcnow()
            
            # Make driver busy
            driver.is_available = False
            db.session.commit()
            
            # Send driver complete order information
            send_driver_complete_order_info(driver_telegram_id, order)
            
            # Notify customer about driver assignment
            notify_customer_driver_assignment(order, driver)
            
            # Notify admin about successful assignment
            notify_admin_successful_assignment(order, driver)
            
            logger.info(f"Order {order_id} accepted by driver {driver.name}")
            return True
            
    except Exception as e:
        logger.error(f"Error in order acceptance workflow: {e}")
        return False

def send_driver_complete_order_info(driver_telegram_id, order):
    """Send complete order information to driver"""
    try:
        # Calculate delivery distance
        restaurant_lat, restaurant_lng = 9.047658, 38.741143  # Restaurant coordinates
        distance = "N/A"
        if order.location_lat and order.location_lng:
            from routes import calculate_distance
            distance = f"{calculate_distance(restaurant_lat, restaurant_lng, order.location_lat, order.location_lng):.1f} km"
        
        message = f"🎯 *ORDER ACCEPTED - Complete Details*\n\n"
        message += f"📋 **Order #{order.id}**\n"
        message += f"💰 **Total**: {order.total_amount:.2f} ETB\n"
        message += f"📍 **Distance**: {distance}\n"
        message += f"💳 **Payment**: {order.payment_method}\n\n"
        
        message += f"👤 **CUSTOMER INFO**\n"
        message += f"📱 Name: {order.customer_name}\n"
        message += f"📞 Phone: {order.customer_phone}\n"
        message += f"🏠 Address: {order.customer_address}\n\n"
        
        message += f"🍽️ **ORDER ITEMS**\n"
        for item in order.items:
            message += f"• {item.get('name', 'Unknown')} x{item.get('quantity', 1)}\n"
        
        message += f"\n🎯 **NEXT STEPS**\n"
        message += f"1. 📍 Share your live location\n"
        message += f"2. 🏪 Go to restaurant and pickup\n"
        message += f"3. 📞 Call customer when ready\n"
        message += f"4. 🚚 Complete delivery\n"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📞 Call Customer",
                        "callback_data": f"call_customer_{order.id}"
                    },
                    {
                        "text": "🏪 Call Restaurant",
                        "callback_data": "call_restaurant"
                    }
                ],
                [
                    {
                        "text": "🗺️ Navigate to Customer",
                        "callback_data": f"navigate_customer_{order.id}"
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
                        "text": "✅ Pickup Complete",
                        "callback_data": f"pickup_complete_{order.id}"
                    }
                ],
                [
                    {
                        "text": "🎯 Driver Panel (GPS)",
                        "callback_data": f"driver_panel_{order.id}"
                    }
                ]
            ]
        }
        
        send_driver_message(driver_telegram_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error sending complete order info: {e}")

def notify_customer_driver_assignment(order, driver):
    """Notify customer about driver assignment"""
    try:
        from bot_minimal import send_message
        
        message = f"🚚 *Driver Assigned to Your Order!*\n\n"
        message += f"📋 Order #{order.id}\n"
        message += f"🚗 Driver: {driver.name}\n"
        message += f"📞 Phone: {driver.phone_number}\n"
        message += f"🕐 Estimated delivery: 20-30 minutes\n\n"
        message += f"📍 You can track your order in real-time!\n"
        message += f"🔔 You'll receive updates at each step:\n"
        message += f"• Order confirmed\n"
        message += f"• Pickup complete\n"
        message += f"• Out for delivery\n"
        message += f"• Delivered\n\n"
        message += f"Thank you for choosing ET-FOOD!"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📞 Call Driver",
                        "url": f"tel:{driver.phone_number}"
                    }
                ],
                [
                    {
                        "text": "📍 Track Order",
                        "callback_data": f"track_order_{order.id}"
                    }
                ]
            ]
        }
        
        send_message(order.telegram_user_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error notifying customer about driver assignment: {e}")

def notify_admin_successful_assignment(order, driver):
    """Notify admin about successful driver assignment"""
    try:
        from bot_minimal import send_message_to_admin
        
        message = f"✅ *Driver Assignment Successful*\n\n"
        message += f"📋 Order #{order.id}\n"
        message += f"🚗 Driver: {driver.name}\n"
        message += f"📞 Driver Phone: {driver.phone_number}\n"
        message += f"👤 Customer: {order.customer_name}\n"
        message += f"📱 Customer Phone: {order.customer_phone}\n"
        message += f"💰 Total: {order.total_amount:.2f} ETB\n"
        message += f"💳 Payment: {order.payment_method}\n\n"
        message += f"🎯 **Status**: Order confirmed and driver assigned\n"
        message += f"📍 **Next**: Driver will pickup and deliver"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📱 View Order Details",
                        "callback_data": f"admin_order_{order.id}"
                    }
                ],
                [
                    {
                        "text": "📊 Live Tracking",
                        "callback_data": f"track_delivery_{order.id}"
                    }
                ]
            ]
        }
        
        admins = AdminUser.query.filter_by(is_active=True).all()
        for admin in admins:
            send_message_to_admin(admin.telegram_user_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error notifying admin about successful assignment: {e}")

def handle_delivery_completion_workflow(driver_telegram_id, order_id):
    """Complete workflow when driver marks delivery as complete"""
    try:
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
            order = Order.query.get(order_id)
            
            if not driver or not order:
                logger.error(f"Driver or order not found for completion workflow")
                return False
            
            # Update order status
            order.status = 'delivered'
            order.updated_at = datetime.utcnow()
            
            # Make driver available again
            driver.is_available = True
            db.session.commit()
            
            # Send completion confirmation to driver
            send_driver_completion_confirmation(driver_telegram_id, order)
            
            # Notify customer about delivery completion
            notify_customer_delivery_completion(order)
            
            # Notify admin about delivery completion
            notify_admin_delivery_completion(order, driver)
            
            logger.info(f"Order {order_id} completed by driver {driver.name}")
            return True
            
    except Exception as e:
        logger.error(f"Error in delivery completion workflow: {e}")
        return False

def send_driver_completion_confirmation(driver_telegram_id, order):
    """Send delivery completion confirmation to driver"""
    try:
        message = f"🎉 *Delivery Completed Successfully!*\n\n"
        message += f"📋 Order #{order.id}\n"
        message += f"💰 Amount: {order.total_amount:.2f} ETB\n"
        message += f"👤 Customer: {order.customer_name}\n"
        message += f"✅ Status: Delivered\n\n"
        message += f"🎯 **You're now available for new orders!**\n"
        message += f"📍 Keep sharing your location to receive more deliveries\n\n"
        message += f"💪 Great job! Ready for the next delivery?"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📊 View My Earnings",
                        "callback_data": "driver_earnings"
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
                        "text": "📋 View Orders",
                        "callback_data": "driver_orders"
                    }
                ]
            ]
        }
        
        send_driver_message(driver_telegram_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error sending completion confirmation: {e}")

def notify_customer_delivery_completion(order):
    """Notify customer about delivery completion"""
    try:
        from bot_minimal import send_message
        
        message = f"🎉 *Your Order Has Been Delivered!*\n\n"
        message += f"📋 Order #{order.id}\n"
        message += f"💰 Total: {order.total_amount:.2f} ETB\n"
        message += f"🕐 Delivered at: {order.updated_at.strftime('%I:%M %p')}\n\n"
        message += f"✅ **Order Status**: Delivered\n\n"
        message += f"🌟 **How was your experience?**\n"
        message += f"Please rate your delivery experience!"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "⭐⭐⭐⭐⭐",
                        "callback_data": f"rate_5_{order.id}"
                    },
                    {
                        "text": "⭐⭐⭐⭐",
                        "callback_data": f"rate_4_{order.id}"
                    }
                ],
                [
                    {
                        "text": "⭐⭐⭐",
                        "callback_data": f"rate_3_{order.id}"
                    },
                    {
                        "text": "⭐⭐",
                        "callback_data": f"rate_2_{order.id}"
                    },
                    {
                        "text": "⭐",
                        "callback_data": f"rate_1_{order.id}"
                    }
                ],
                [
                    {
                        "text": "💬 Leave Feedback",
                        "callback_data": "leave_feedback"
                    }
                ]
            ]
        }
        
        send_message(order.telegram_user_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error notifying customer about delivery completion: {e}")

def notify_admin_delivery_completion(order, driver):
    """Notify admin about delivery completion"""
    try:
        from bot_minimal import send_message_to_admin
        
        message = f"🎉 *Delivery Completed Successfully*\n\n"
        message += f"📋 Order #{order.id}\n"
        message += f"🚗 Driver: {driver.name}\n"
        message += f"👤 Customer: {order.customer_name}\n"
        message += f"💰 Total: {order.total_amount:.2f} ETB\n"
        message += f"💳 Payment: {order.payment_method}\n"
        message += f"🕐 Completed: {order.updated_at.strftime('%I:%M %p')}\n\n"
        message += f"✅ **Status**: Successfully delivered\n"
        message += f"🎯 **Driver**: Available for new orders\n"
        message += f"📊 **Performance**: On time delivery"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📊 View Statistics",
                        "callback_data": "admin_stats"
                    }
                ],
                [
                    {
                        "text": "📋 View All Orders",
                        "callback_data": "admin_orders"
                    }
                ]
            ]
        }
        
        admins = AdminUser.query.filter_by(is_active=True).all()
        for admin in admins:
            send_message_to_admin(admin.telegram_user_id, message, keyboard=keyboard)
            
    except Exception as e:
        logger.error(f"Error notifying admin about delivery completion: {e}")