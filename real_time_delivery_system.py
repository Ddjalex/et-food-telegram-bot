"""
Real-time Delivery System with Complete Order Workflow
Handles driver assignment, location tracking, and delivery completion
"""

import logging
from datetime import datetime, timedelta
from models import Driver, Order, AdminUser
from extensions import db
from app import app
from driver_bot import send_driver_message, notify_driver_assignment_via_driver_bot
from enhanced_driver_system import (
    handle_order_acceptance_workflow,
    handle_delivery_completion_workflow
)
import threading
import time
import math

logger = logging.getLogger(__name__)

class RealTimeDeliverySystem:
    """Manages real-time delivery operations"""
    
    def __init__(self):
        self.active_deliveries = {}  # Track active deliveries
        self.driver_assignments = {}  # Track driver assignments
        
    def calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two coordinates using Haversine formula"""
        if not all([lat1, lng1, lat2, lng2]):
            return float('inf')
            
        R = 6371  # Earth's radius in km
        dLat = math.radians(lat2 - lat1)
        dLng = math.radians(lng2 - lng1)
        a = (math.sin(dLat/2) * math.sin(dLat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dLng/2) * math.sin(dLng/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def find_nearby_drivers(self, order_id, max_distance=10.0):
        """Find available drivers within specified distance"""
        try:
            with app.app_context():
                order = Order.query.get(order_id)
                if not order:
                    logger.error(f"Order {order_id} not found")
                    return []
                
                # Restaurant coordinates (fixed location)
                restaurant_lat, restaurant_lng = 9.047658, 38.741143
                
                # Get available drivers with recent location updates
                cutoff_time = datetime.utcnow() - timedelta(minutes=10)
                available_drivers = Driver.query.filter(
                    Driver.is_active == True,
                    Driver.is_available == True,
                    Driver.is_approved == True,
                    Driver.telegram_user_id != None,
                    Driver.last_location_update > cutoff_time
                ).all()
                
                nearby_drivers = []
                for driver in available_drivers:
                    if driver.current_lat and driver.current_lng:
                        distance = self.calculate_distance(
                            restaurant_lat, restaurant_lng,
                            driver.current_lat, driver.current_lng
                        )
                        if distance <= max_distance:
                            nearby_drivers.append({
                                'driver': driver,
                                'distance': distance
                            })
                
                # Sort by distance
                nearby_drivers.sort(key=lambda x: x['distance'])
                
                # Limit to top 3 drivers
                return nearby_drivers[:3]
                
        except Exception as e:
            logger.error(f"Error finding nearby drivers: {e}")
            return []
    
    def notify_drivers_about_order(self, order_id):
        """Send order notifications to nearby drivers"""
        try:
            nearby_drivers = self.find_nearby_drivers(order_id)
            
            if not nearby_drivers:
                logger.warning(f"No nearby drivers found for order {order_id}")
                self.notify_admin_no_drivers_available(order_id)
                return False
            
            with app.app_context():
                order = Order.query.get(order_id)
                if not order:
                    return False
                
                # Send notifications to all nearby drivers
                for driver_info in nearby_drivers:
                    driver = driver_info['driver']
                    distance = driver_info['distance']
                    
                    # Send enhanced notification with order details
                    self.send_order_notification_to_driver(driver, order, distance)
                    
                logger.info(f"Sent order notifications to {len(nearby_drivers)} drivers for order {order_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error notifying drivers about order: {e}")
            return False
    
    def send_order_notification_to_driver(self, driver, order, distance):
        """Send detailed order notification to driver"""
        try:
            message = f"🚚 *NEW DELIVERY REQUEST*\n\n"
            message += f"📋 **Order #{order.id}**\n"
            message += f"📍 **Distance**: {distance:.1f} km\n\n"
            
            message += f"👤 **Customer**: {order.customer_name}\n"
            message += f"📞 **Phone**: {order.customer_phone}\n"
            message += f"🏠 **Address**: {order.customer_address}\n\n"
            
            message += f"🍽️ **Items**: {len(order.items)} items\n"
            for item in order.items[:3]:  # Show first 3 items
                message += f"• {item.get('name', 'Unknown')} x{item.get('quantity', 1)}\n"
            
            if len(order.items) > 3:
                message += f"• ... and {len(order.items) - 3} more items\n"
            
            message += f"\n⏰ **Accept within 1 minute** or order will go to next driver\n"
            message += f"💡 **Delivery fee will be paid upon completion**"
            
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
                    ],
                    [
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order.id}"
                        },
                        {
                            "text": "🗺️ View Location",
                            "callback_data": f"view_location_{order.id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver.telegram_user_id, message, keyboard=keyboard)
            
            # Start countdown timer for order acceptance
            self.start_order_acceptance_timer(order.id, driver.telegram_user_id)
            
        except Exception as e:
            logger.error(f"Error sending order notification to driver: {e}")
    
    def start_order_acceptance_timer(self, order_id, driver_telegram_id):
        """Start 1-minute timer for order acceptance"""
        def timeout_handler():
            time.sleep(60)  # Wait 1 minute
            
            try:
                with app.app_context():
                    order = Order.query.get(order_id)
                    if order and order.status == 'pending':
                        # Order not accepted, notify driver and reassign
                        send_driver_message(
                            driver_telegram_id,
                            f"⏰ Order #{order_id} expired. Order has been reassigned to another driver."
                        )
                        
                        # Try to reassign to next available driver
                        self.reassign_order_to_next_driver(order_id)
                        
            except Exception as e:
                logger.error(f"Error in timeout handler: {e}")
        
        thread = threading.Thread(target=timeout_handler)
        thread.daemon = True
        thread.start()
    
    def reassign_order_to_next_driver(self, order_id):
        """Reassign order to next available driver"""
        try:
            # Find next available drivers
            nearby_drivers = self.find_nearby_drivers(order_id)
            
            if nearby_drivers:
                # Get drivers who haven't been notified yet
                with app.app_context():
                    order = Order.query.get(order_id)
                    if order and order.status == 'pending':
                        # Send to next driver
                        next_driver = nearby_drivers[0]['driver']
                        distance = nearby_drivers[0]['distance']
                        
                        self.send_order_notification_to_driver(next_driver, order, distance)
                        logger.info(f"Reassigned order {order_id} to driver {next_driver.name}")
            else:
                self.notify_admin_no_drivers_available(order_id)
                
        except Exception as e:
            logger.error(f"Error reassigning order: {e}")
    
    def notify_admin_no_drivers_available(self, order_id):
        """Notify admin when no drivers are available"""
        try:
            with app.app_context():
                order = Order.query.get(order_id)
                if not order:
                    return
                
                message = f"⚠️ *No Drivers Available*\n\n"
                message += f"📋 Order #{order.id}\n"
                message += f"👤 Customer: {order.customer_name}\n"
                message += f"📞 Phone: {order.customer_phone}\n"
                message += f"💰 Total: {order.total_amount:.2f} ETB\n\n"
                message += f"❌ **Issue**: No drivers within 10km radius\n"
                message += f"⏰ **Time**: {datetime.utcnow().strftime('%I:%M %p')}\n\n"
                message += f"🔧 **Action Required**: Manual driver assignment needed"
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "🚚 Assign Driver Manually",
                                "callback_data": f"manual_assign_{order.id}"
                            }
                        ]
                    ]
                }
                
                admins = AdminUser.query.filter_by(is_active=True).all()
                for admin in admins:
                    from bot_minimal import send_message_to_admin
                    send_message_to_admin(admin.telegram_user_id, message, keyboard=keyboard)
                
        except Exception as e:
            logger.error(f"Error notifying admin about no drivers: {e}")
    
    def handle_driver_order_acceptance(self, driver_telegram_id, order_id):
        """Handle when driver accepts an order"""
        try:
            with app.app_context():
                driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
                order = Order.query.get(order_id)
                
                if not driver or not order:
                    logger.error(f"Driver or order not found for acceptance")
                    return False
                
                if order.status != 'pending':
                    send_driver_message(driver_telegram_id, f"❌ Order #{order_id} is no longer available.")
                    return False
                
                # Use enhanced order acceptance workflow
                success = handle_order_acceptance_workflow(driver_telegram_id, order_id)
                
                if success:
                    # Track active delivery
                    self.active_deliveries[order_id] = {
                        'driver_id': driver.id,
                        'driver_telegram_id': driver_telegram_id,
                        'start_time': datetime.utcnow(),
                        'status': 'assigned'
                    }
                    
                    logger.info(f"Order {order_id} accepted by driver {driver.name}")
                    
                return success
                
        except Exception as e:
            logger.error(f"Error handling driver order acceptance: {e}")
            return False
    
    def handle_driver_order_rejection(self, driver_telegram_id, order_id):
        """Handle when driver rejects an order"""
        try:
            send_driver_message(driver_telegram_id, f"❌ Order #{order_id} declined. Looking for other drivers...")
            
            # Try to reassign to next available driver
            self.reassign_order_to_next_driver(order_id)
            
            logger.info(f"Order {order_id} rejected by driver {driver_telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling driver order rejection: {e}")
            return False
    
    def handle_pickup_completion(self, driver_telegram_id, order_id):
        """Handle pickup completion"""
        try:
            with app.app_context():
                order = Order.query.get(order_id)
                driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
                
                if not order or not driver:
                    return False
                
                # Update order status
                order.status = 'out_for_delivery'
                order.updated_at = datetime.utcnow()
                db.session.commit()
                
                # Update active delivery tracking
                if order_id in self.active_deliveries:
                    self.active_deliveries[order_id]['status'] = 'out_for_delivery'
                    self.active_deliveries[order_id]['pickup_time'] = datetime.utcnow()
                
                # Send notifications
                self.notify_pickup_completion(order, driver)
                
                logger.info(f"Pickup completed for order {order_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling pickup completion: {e}")
            return False
    
    def notify_pickup_completion(self, order, driver):
        """Send pickup completion notifications"""
        try:
            # Notify customer
            from bot_minimal import send_message
            customer_message = f"🚚 *Your Order is Out for Delivery!*\n\n"
            customer_message += f"📋 Order #{order.id}\n"
            customer_message += f"🚗 Driver: {driver.name}\n"
            customer_message += f"📞 Phone: {driver.phone_number}\n"
            customer_message += f"🕐 Estimated arrival: 15-25 minutes\n\n"
            customer_message += f"📍 You can call the driver if needed!"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Driver",
                            "url": f"tel:{driver.phone_number}"
                        }
                    ]
                ]
            }
            
            send_message(order.telegram_user_id, customer_message, keyboard=keyboard)
            
            # Notify admin
            from bot_minimal import send_message_to_admin
            admin_message = f"🚚 *Pickup Complete*\n\n"
            admin_message += f"📋 Order #{order.id}\n"
            admin_message += f"🚗 Driver: {driver.name}\n"
            admin_message += f"👤 Customer: {order.customer_name}\n"
            admin_message += f"📞 Phone: {order.customer_phone}\n"
            admin_message += f"🕐 Pickup Time: {order.updated_at.strftime('%I:%M %p')}\n\n"
            admin_message += f"✅ Status: Out for delivery"
            
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                send_message_to_admin(admin.telegram_user_id, admin_message)
                
        except Exception as e:
            logger.error(f"Error notifying pickup completion: {e}")
    
    def handle_delivery_completion(self, driver_telegram_id, order_id):
        """Handle delivery completion"""
        try:
            # Use enhanced delivery completion workflow
            success = handle_delivery_completion_workflow(driver_telegram_id, order_id)
            
            if success and order_id in self.active_deliveries:
                # Remove from active deliveries
                del self.active_deliveries[order_id]
                
            return success
            
        except Exception as e:
            logger.error(f"Error handling delivery completion: {e}")
            return False

# Global instance
delivery_system = RealTimeDeliverySystem()

def process_order_for_delivery(order_id):
    """Process new order for delivery assignment"""
    try:
        # Run in background thread to avoid blocking
        thread = threading.Thread(target=delivery_system.notify_drivers_about_order, args=(order_id,))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started delivery process for order {order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing order for delivery: {e}")
        return False

def get_active_deliveries():
    """Get all active deliveries"""
    return delivery_system.active_deliveries

def get_delivery_statistics():
    """Get delivery statistics"""
    try:
        with app.app_context():
            active_count = len(delivery_system.active_deliveries)
            
            total_orders = Order.query.count()
            completed_orders = Order.query.filter_by(status='delivered').count()
            pending_orders = Order.query.filter_by(status='pending').count()
            
            return {
                'active_deliveries': active_count,
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'pending_orders': pending_orders,
                'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0
            }
            
    except Exception as e:
        logger.error(f"Error getting delivery statistics: {e}")
        return {
            'active_deliveries': 0,
            'total_orders': 0,
            'completed_orders': 0,
            'pending_orders': 0,
            'completion_rate': 0
        }