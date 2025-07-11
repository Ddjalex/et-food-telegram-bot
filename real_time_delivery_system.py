"""
Real-Time Delivery System for ET-FOOD
Handles complete delivery workflow with live tracking and notifications
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from models import Driver, Order, AdminUser
from extensions import db
from driver_bot import send_driver_message, notify_driver_order_assignment
from bot_minimal import send_message, send_message_to_admin

logger = logging.getLogger(__name__)

class RealTimeDeliverySystem:
    """Real-time delivery system with live tracking and automated workflow"""
    
    def __init__(self):
        self.active_deliveries = {}  # Track ongoing deliveries
        self.driver_locations = {}   # Track driver locations
        
    def process_new_order(self, order_id):
        """Process new order and initiate delivery workflow"""
        try:
            from app import app
            with app.app_context():
                order = db.session.get(Order, order_id)
                if not order:
                    logger.error(f"Order {order_id} not found")
                    return False
                
                # Find nearby available drivers
                nearby_drivers = self.find_nearby_drivers(order)
                
                if not nearby_drivers:
                    # No drivers available
                    self.notify_admin_no_drivers(order)
                    return False
                
                # Notify first 3 drivers
                for driver in nearby_drivers[:3]:
                    self.notify_driver_about_order(driver, order)
                
                logger.info(f"Order {order_id} notifications sent to {len(nearby_drivers[:3])} drivers")
                return True
                
        except Exception as e:
            logger.error(f"Error processing new order {order_id}: {e}")
            return False
    
    def find_nearby_drivers(self, order):
        """Find nearby available drivers within delivery radius"""
        try:
            # Get all active, approved, and available drivers
            available_drivers = Driver.query.filter_by(
                is_active=True, 
                is_approved=True, 
                is_available=True
            ).all()
            
            # Filter drivers with recent location updates (within 10 minutes)
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            nearby_drivers = []
            
            for driver in available_drivers:
                # Check if driver has recent location update
                if driver.last_location_update and driver.last_location_update > ten_minutes_ago:
                    # For now, add all drivers with recent location
                    # In production, calculate actual distance
                    nearby_drivers.append(driver)
            
            return nearby_drivers
            
        except Exception as e:
            logger.error(f"Error finding nearby drivers: {e}")
            return []
    
    def notify_driver_about_order(self, driver, order):
        """Notify driver about new order assignment"""
        try:
            if not driver.telegram_user_id:
                logger.warning(f"Driver {driver.name} has no telegram_user_id")
                return False
            
            # Calculate distance (placeholder - implement actual distance calculation)
            distance = "2.5 km"  # Placeholder
            
            message = f"🚚 *New Delivery Request*\n\n"
            message += f"📋 **Order #{order.id}**\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"📍 Distance: {distance}\n"
            message += f"💰 Total: {order.total_amount:.2f} ETB\n\n"
            message += f"📍 **Address:** {order.customer_address}\n"
            message += f"💳 **Payment:** {order.payment_method}\n\n"
            message += f"⏰ You have 60 seconds to accept this order"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Accept Order",
                            "callback_data": f"accept_order_{order.id}"
                        },
                        {
                            "text": "❌ Decline",
                            "callback_data": f"decline_order_{order.id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver.telegram_user_id, message, keyboard=keyboard)
            
            # Start 60-second timer for auto-reassignment
            self.start_order_timer(order.id, driver.telegram_user_id)
            
            logger.info(f"Order {order.id} notification sent to driver {driver.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error notifying driver about order: {e}")
            return False
    
    def start_order_timer(self, order_id, driver_telegram_id):
        """Start 60-second timer for order acceptance"""
        def timeout_handler():
            time.sleep(60)  # Wait 60 seconds
            self.handle_order_timeout(order_id, driver_telegram_id)
        
        timer_thread = threading.Thread(target=timeout_handler)
        timer_thread.daemon = True
        timer_thread.start()
    
    def handle_order_timeout(self, order_id, driver_telegram_id):
        """Handle order timeout - reassign to next driver"""
        try:
            from app import app
            with app.app_context():
                order = db.session.get(Order, order_id)
                if not order or order.status != 'pending':
                    # Order was already accepted or cancelled
                    return
                
                # Find next available driver
                self.reassign_order_to_next_driver(order_id, exclude_driver_id=driver_telegram_id)
                
        except Exception as e:
            logger.error(f"Error handling order timeout: {e}")
    
    def reassign_order_to_next_driver(self, order_id, exclude_driver_id=None):
        """Reassign order to next available driver"""
        try:
            from app import app
            with app.app_context():
                order = db.session.get(Order, order_id)
                if not order:
                    return False
                
                # Find next available driver (excluding the one who timed out)
                available_drivers = Driver.query.filter_by(
                    is_active=True,
                    is_approved=True,
                    is_available=True
                ).all()
                
                if exclude_driver_id:
                    available_drivers = [d for d in available_drivers if d.telegram_user_id != exclude_driver_id]
                
                if available_drivers:
                    next_driver = available_drivers[0]
                    self.notify_driver_about_order(next_driver, order)
                    logger.info(f"Order {order_id} reassigned to driver {next_driver.name}")
                else:
                    # No more drivers available
                    self.notify_admin_no_drivers(order)
                    logger.warning(f"No more drivers available for order {order_id}")
                
        except Exception as e:
            logger.error(f"Error reassigning order: {e}")
    
    def handle_order_acceptance(self, driver_telegram_id, order_id):
        """Handle order acceptance by driver"""
        try:
            from app import app
            with app.app_context():
                order = db.session.get(Order, order_id)
                driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
                
                if not order or not driver:
                    return False
                
                # Update order status
                order.status = 'confirmed'
                order.assigned_driver_id = driver.id
                
                # Make driver unavailable
                driver.is_available = False
                
                db.session.commit()
                
                # Send complete order info to driver
                self.send_complete_order_info_to_driver(driver, order)
                
                # Notify customer about driver assignment
                self.notify_customer_driver_assigned(order, driver)
                
                # Notify admin
                self.notify_admin_driver_assigned(order, driver)
                
                logger.info(f"Order {order_id} accepted by driver {driver.name}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling order acceptance: {e}")
            return False
    
    def send_complete_order_info_to_driver(self, driver, order):
        """Send complete order information to driver"""
        try:
            message = f"🎉 *Order Accepted Successfully!*\n\n"
            message += f"📋 **Order #{order.id}**\n"
            message += f"👤 **Customer:** {order.customer_name}\n"
            message += f"📞 **Phone:** {order.customer_phone}\n"
            message += f"📍 **Address:** {order.customer_address}\n"
            message += f"💰 **Total:** {order.total_amount:.2f} ETB\n"
            message += f"💳 **Payment:** {order.payment_method}\n\n"
            
            # Add order items
            if order.items:
                message += f"🍽️ **Order Items:**\n"
                import json
                items = json.loads(order.items)
                for item in items:
                    message += f"• {item.get('name', 'Unknown')} x{item.get('quantity', 1)}\n"
            
            message += f"\n🚚 **Next Steps:**\n"
            message += f"1. Share your live location\n"
            message += f"2. Pick up from restaurant\n"
            message += f"3. Deliver to customer\n"
            message += f"4. Complete delivery\n\n"
            
            # GPS coordinates if available
            if order.location_lat and order.location_lng:
                message += f"📍 **GPS:** {order.location_lat}, {order.location_lng}\n\n"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order.id}"
                        },
                        {
                            "text": "📍 Navigate",
                            "callback_data": f"navigate_customer_{order.id}"
                        }
                    ],
                    [
                        {
                            "text": "📞 Call Restaurant",
                            "callback_data": f"call_restaurant"
                        },
                        {
                            "text": "🏪 Navigate to Restaurant",
                            "callback_data": f"navigate_restaurant"
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
                            "text": "✅ Picked Up",
                            "callback_data": f"pickup_complete_{order.id}"
                        },
                        {
                            "text": "🏁 Delivered",
                            "callback_data": f"delivery_complete_{order.id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver.telegram_user_id, message, keyboard=keyboard)
            
            # Request live location
            self.request_live_location(driver.telegram_user_id, order.id)
            
        except Exception as e:
            logger.error(f"Error sending complete order info: {e}")
    
    def request_live_location(self, driver_telegram_id, order_id):
        """Request live location from driver"""
        try:
            message = f"📍 *Live Location Required*\n\n"
            message += f"🚚 **Order #{order_id}**\n\n"
            message += f"Please share your live location for real-time tracking:\n"
            message += f"• Customer can track your progress\n"
            message += f"• Admin can monitor delivery\n"
            message += f"• System provides accurate ETAs\n\n"
            message += f"📱 **How to share:**\n"
            message += f"1. Tap 'Share Location' button\n"
            message += f"2. Select 'Live Location'\n"
            message += f"3. Choose 30 minutes duration\n"
            message += f"4. Tap 'Send'\n\n"
            message += f"⚠️ Keep sharing until delivery complete!"
            
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
            
            send_driver_message(driver_telegram_id, message, keyboard=keyboard)
            
        except Exception as e:
            logger.error(f"Error requesting live location: {e}")
    
    def notify_customer_driver_assigned(self, order, driver):
        """Notify customer about driver assignment"""
        try:
            message = f"🚚 *Driver Assigned to Your Order!*\n\n"
            message += f"📋 Order #{order.id}\n"
            message += f"🚗 Driver: {driver.name}\n"
            message += f"📞 Phone: {driver.phone_number}\n"
            message += f"🚗 Vehicle: {driver.vehicle_type}\n\n"
            message += f"📍 Your driver will share live location for tracking\n"
            message += f"🕐 Estimated delivery: 15-30 minutes\n\n"
            message += f"You can track the delivery progress in real-time!"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Driver",
                            "url": f"tel:{driver.phone_number}"
                        },
                        {
                            "text": "📍 Track Location",
                            "callback_data": f"track_driver_{order.id}"
                        }
                    ]
                ]
            }
            
            send_message(order.telegram_user_id, message, keyboard=keyboard)
            
        except Exception as e:
            logger.error(f"Error notifying customer: {e}")
    
    def notify_admin_driver_assigned(self, order, driver):
        """Notify admin about driver assignment"""
        try:
            message = f"✅ *Driver Assignment Successful*\n\n"
            message += f"📋 Order #{order.id}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"💰 Total: {order.total_amount:.2f} ETB\n\n"
            message += f"🚗 **Assigned Driver:**\n"
            message += f"• Name: {driver.name}\n"
            message += f"• Phone: {driver.phone_number}\n"
            message += f"• Vehicle: {driver.vehicle_type}\n\n"
            message += f"📍 Live tracking will be available once driver starts sharing location"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Driver",
                            "url": f"tel:{driver.phone_number}"
                        },
                        {
                            "text": "📍 Track Delivery",
                            "callback_data": f"track_delivery_{order.id}"
                        }
                    ]
                ]
            }
            
            # Send to all admins
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, message, keyboard=keyboard)
            
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
    
    def notify_admin_no_drivers(self, order):
        """Notify admin when no drivers are available"""
        try:
            message = f"⚠️ *No Drivers Available*\n\n"
            message += f"📋 Order #{order.id}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"💰 Total: {order.total_amount:.2f} ETB\n\n"
            message += f"❌ No available drivers found for this order.\n"
            message += f"Please manually assign a driver or contact available drivers directly."
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "👥 Manual Assignment",
                            "callback_data": f"manual_assign_{order.id}"
                        }
                    ]
                ]
            }
            
            # Send to all admins
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, message, keyboard=keyboard)
            
        except Exception as e:
            logger.error(f"Error notifying admin about no drivers: {e}")

# Create global instance
delivery_system = RealTimeDeliverySystem()

def process_new_order(order_id):
    """Process new order through real-time delivery system"""
    return delivery_system.process_new_order(order_id)

def handle_order_acceptance(driver_telegram_id, order_id):
    """Handle order acceptance"""
    return delivery_system.handle_order_acceptance(driver_telegram_id, order_id)