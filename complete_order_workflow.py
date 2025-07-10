"""
Complete Order Workflow System - Simplified Version
Handles the entire order lifecycle from customer checkout to driver delivery
"""

import os
import logging
from datetime import datetime, timedelta
import math

# Import models and database
from models import Order, Driver, AdminUser
from extensions import db
from bot_minimal import send_order_notification, notify_customer_status_change

logger = logging.getLogger(__name__)

class OrderWorkflowManager:
    """Manages the complete order workflow"""
    
    def __init__(self):
        self.restaurant_location = (9.145, 40.489658)  # ET-FOOD Kitchen coordinates
        self.max_driver_distance = 10.0  # Maximum distance in km
        
    def calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two coordinates using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def find_nearby_drivers(self, order_id):
        """Find and notify nearby drivers about new order"""
        try:
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            # Find available drivers - first check with location data, then fallback to all available drivers
            available_drivers = Driver.query.filter_by(
                is_active=True,
                is_available=True,
                is_approved=True
            ).filter(
                Driver.current_lat.isnot(None),
                Driver.current_lng.isnot(None),
                Driver.last_location_update > datetime.utcnow() - timedelta(minutes=10)
            ).all()
            
            # If no drivers with location data, fall back to all available drivers
            if not available_drivers:
                logger.info(f"No drivers with location data found, falling back to all available drivers")
                available_drivers = Driver.query.filter_by(
                    is_active=True,
                    is_available=True,
                    is_approved=True
                ).all()
            
            if not available_drivers:
                logger.warning(f"No available drivers found for order {order_id}")
                self.notify_admin_no_drivers(order)
                return False
            
            # Calculate distances and sort by proximity
            driver_distances = []
            for driver in available_drivers:
                if driver.current_lat and driver.current_lng:
                    # Driver has location data - calculate distance
                    distance = self.calculate_distance(
                        self.restaurant_location[0],
                        self.restaurant_location[1],
                        driver.current_lat,
                        driver.current_lng
                    )
                    
                    if distance <= self.max_driver_distance:
                        driver_distances.append((driver, distance))
                else:
                    # Driver has no location data - use default distance for notification
                    logger.info(f"Driver {driver.name} has no location data, using default distance")
                    driver_distances.append((driver, 5.0))  # Default 5km distance
            
            if not driver_distances:
                logger.warning(f"No available drivers found for order {order_id}")
                self.notify_admin_no_drivers(order)
                return False
            
            # Sort by distance and take top 3
            driver_distances.sort(key=lambda x: x[1])
            nearest_drivers = driver_distances[:3]
            
            logger.info(f"Found {len(nearest_drivers)} nearby drivers for order {order_id}")
            
            # Notify drivers (first-come-first-served)
            for driver, distance in nearest_drivers:
                self.notify_driver_about_order(driver, order, distance)
            
            return True
            
        except Exception as e:
            logger.error(f"Error finding nearby drivers for order {order_id}: {e}")
            return False
    
    def notify_driver_about_order(self, driver, order, distance):
        """Send order notification to driver with countdown timer"""
        try:
            from driver_bot import send_driver_message
            
            # Calculate customer distance
            customer_coords = (order.location_lat or 9.165, order.location_lng or 40.510)
            customer_distance = self.calculate_distance(
                self.restaurant_location[0],
                self.restaurant_location[1],
                customer_coords[0],
                customer_coords[1]
            )
            
            # Create notification message
            message = f"🚚 *NEW DELIVERY REQUEST* 🚚\n\n"
            message += f"📋 Order #{order.id}\n"
            message += f"🏪 Restaurant: ET-FOOD Kitchen\n"
            message += f"📍 Distance to Restaurant: {distance:.1f} km\n"
            message += f"📍 Distance to Customer: {customer_distance:.1f} km\n\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"📍 Address: {order.customer_address}\n"
            message += f"💰 Total Amount: {order.total_amount:.2f} ETB\n"
            message += f"💳 Payment: {order.payment_method}\n\n"
            message += f"⏰ *First to accept gets the order!*"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ ACCEPT ORDER",
                            "callback_data": f"driver_accept_{order.id}"
                        },
                        {
                            "text": "❌ REJECT",
                            "callback_data": f"driver_reject_{order.id}"
                        }
                    ],
                    [
                        {
                            "text": "📞 Call Restaurant",
                            "callback_data": f"call_restaurant_{order.id}"
                        },
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order.id}"
                        }
                    ]
                ]
            }
            
            # Send notification
            send_driver_message(driver.telegram_user_id, message, keyboard)
            
            logger.info(f"Notified driver {driver.name} (ID: {driver.telegram_user_id}) about order {order.id}")
            
        except Exception as e:
            logger.error(f"Error notifying driver {driver.name}: {e}")

    def handle_order_status_update(self, order_id, old_status, new_status):
        """Handle order status updates and trigger appropriate notifications"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return
            
            # Status-specific handling
            if new_status == 'confirmed' and old_status == 'pending':
                # Admin confirmed order - search for drivers
                logger.info(f"Order {order_id} confirmed by admin - searching for drivers")
                self.find_nearby_drivers(order_id)
                
            elif new_status == 'preparing' and order.driver_id:
                # Order being prepared - notify assigned driver
                self.notify_driver_preparing(order)
                
            elif new_status == 'out_for_delivery' and order.driver_id:
                # Order ready for delivery
                self.notify_driver_ready_for_delivery(order)
                
            elif new_status == 'delivered':
                # Order completed - update driver availability
                self.handle_order_completion(order)
                
        except Exception as e:
            logger.error(f"Error handling status update for order {order_id}: {e}")
    
    def notify_driver_preparing(self, order):
        """Notify driver that order is being prepared"""
        try:
            from driver_bot import send_driver_message
            driver = Driver.query.get(order.driver_id)
            if not driver or not driver.telegram_user_id:
                return
            
            message = f"👨‍🍳 *Order Being Prepared*\n\n"
            message += f"📋 Order #{order.id} is now being prepared!\n"
            message += f"🎯 Please get ready to collect from restaurant.\n"
            message += f"📞 Restaurant: +251-911-123-456\n"
            message += f"📍 Location: ET-FOOD Kitchen\n\n"
            message += f"⏰ Estimated preparation time: 15-20 minutes"
            
            send_driver_message(driver.telegram_user_id, message)
            
        except Exception as e:
            logger.error(f"Error notifying driver about preparation: {e}")
    
    def notify_driver_ready_for_delivery(self, order):
        """Notify driver that order is ready for pickup/delivery"""
        try:
            from driver_bot import send_driver_message
            driver = Driver.query.get(order.driver_id)
            if not driver or not driver.telegram_user_id:
                return
            
            message = f"🚚 *Order Ready for Delivery!*\n\n"
            message += f"📋 Order #{order.id} is ready for pickup!\n"
            message += f"🎯 Please collect from restaurant and deliver to customer.\n\n"
            message += f"📞 Customer: {order.customer_phone}\n"
            message += f"📍 Delivery Address: {order.customer_address}\n"
            message += f"💰 Total Amount: {order.total_amount:.2f} ETB\n"
            message += f"💳 Payment Method: {order.payment_method}"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order.id}"
                        },
                        {
                            "text": "📞 Call Restaurant",
                            "callback_data": f"call_restaurant_{order.id}"
                        }
                    ],
                    [
                        {
                            "text": "📍 Share Live Location",
                            "callback_data": f"driver_location_{order.id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver.telegram_user_id, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error notifying driver about ready delivery: {e}")
    
    def handle_order_completion(self, order):
        """Handle order completion - make driver available again"""
        try:
            if order.driver_id:
                driver = Driver.query.get(order.driver_id)
                if driver:
                    driver.is_available = True
                    db.session.commit()
                    
                    if driver.telegram_user_id:
                        from driver_bot import send_driver_message
                        message = f"✅ *Order Completed!*\n\n"
                        message += f"📋 Order #{order.id} has been delivered successfully!\n"
                        message += f"💰 You earned: {order.total_amount * 0.1:.2f} ETB (10% commission)\n\n"
                        message += f"🎯 You are now available for new orders.\n"
                        message += f"Great job! 👍"
                        
                        send_driver_message(driver.telegram_user_id, message)
                        
        except Exception as e:
            logger.error(f"Error handling order completion: {e}")
    
    def notify_admin_no_drivers(self, order):
        """Notify admin when no drivers are available"""
        try:
            from bot_minimal import send_message_to_admin
            message = f"⚠️ *NO DRIVERS AVAILABLE*\n\n"
            message += f"📋 Order #{order.id}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
            message += f"❌ No drivers found within {self.max_driver_distance}km radius\n"
            message += f"🎯 Please check driver availability or assign manually"
            
            # Send to admin (for now just log it)
            logger.warning(f"Admin notification: {message}")
                
        except Exception as e:
            logger.error(f"Error notifying admin about no drivers: {e}")

# Global instance
workflow_manager = OrderWorkflowManager()

def process_new_order(order_id):
    """Process a new order - called when customer places order"""
    try:
        # Send notification to admins first
        send_order_notification(order_id)
        
        # Note: Driver notification will be triggered when admin confirms the order
        logger.info(f"New order {order_id} processed - awaiting admin confirmation")
        
    except Exception as e:
        logger.error(f"Error processing new order {order_id}: {e}")

def handle_order_status_change(order_id, old_status, new_status):
    """Handle order status changes"""
    try:
        # Notify customer
        notify_customer_status_change(order_id, new_status)
        
        # Handle driver workflow
        workflow_manager.handle_order_status_update(order_id, old_status, new_status)
        
    except Exception as e:
        logger.error(f"Error handling status change for order {order_id}: {e}")
    
    def notify_admin_no_drivers(self, order):
        """Notify admin when no drivers are available"""
        try:
            admins = AdminUser.query.filter_by(is_active=True).all()
            
            message = f"⚠️ *NO DRIVERS AVAILABLE*\n\n"
            message += f"📋 Order #{order.id}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Phone: {order.customer_phone}\n"
            message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
            message += f"❌ No drivers found within {self.max_driver_distance}km radius\n"
            message += f"🎯 Please check driver availability or assign manually"
            
            for admin in admins:
                from bot_minimal import send_message_to_admin
                send_message_to_admin(admin.telegram_user_id, message)
                
        except Exception as e:
            logger.error(f"Error notifying admin about no drivers: {e}")
    
    def handle_order_status_update(self, order_id, old_status, new_status):
        """Handle order status updates and trigger appropriate notifications"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return
            
            # Status-specific handling
            if new_status == 'confirmed' and old_status == 'pending':
                # Admin confirmed order - search for drivers
                logger.info(f"Order {order_id} confirmed by admin - searching for drivers")
                threading.Thread(
                    target=self.find_nearby_drivers,
                    args=(order_id,),
                    daemon=True
                ).start()
                
            elif new_status == 'preparing' and order.driver_id:
                # Order being prepared - notify assigned driver
                self.notify_driver_preparing(order)
                
            elif new_status == 'out_for_delivery' and order.driver_id:
                # Order ready for delivery
                self.notify_driver_ready_for_delivery(order)
                
            elif new_status == 'delivered':
                # Order completed - update driver availability
                self.handle_order_completion(order)
                
        except Exception as e:
            logger.error(f"Error handling status update for order {order_id}: {e}")
    
    def notify_driver_preparing(self, order):
        """Notify driver that order is being prepared"""
        try:
            driver = Driver.query.get(order.driver_id)
            if not driver or not driver.telegram_user_id:
                return
            
            message = f"👨‍🍳 *Order Being Prepared*\n\n"
            message += f"📋 Order #{order.id} is now being prepared!\n"
            message += f"🎯 Please get ready to collect from restaurant.\n"
            message += f"📞 Restaurant: +251-911-123-456\n"
            message += f"📍 Location: ET-FOOD Kitchen\n\n"
            message += f"⏰ Estimated preparation time: 15-20 minutes"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Restaurant",
                            "callback_data": f"call_restaurant_{order.id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver.telegram_user_id, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error notifying driver about preparation: {e}")
    
    def notify_driver_ready_for_delivery(self, order):
        """Notify driver that order is ready for pickup/delivery"""
        try:
            driver = Driver.query.get(order.driver_id)
            if not driver or not driver.telegram_user_id:
                return
            
            message = f"🚚 *Order Ready for Delivery!*\n\n"
            message += f"📋 Order #{order.id} is ready for pickup!\n"
            message += f"🎯 Please collect from restaurant and deliver to customer.\n\n"
            message += f"📞 Customer: {order.customer_phone}\n"
            message += f"📍 Delivery Address: {order.customer_address}\n"
            message += f"💰 Total Amount: {order.total_amount:.2f} ETB\n"
            message += f"💳 Payment Method: {order.payment_method}"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "callback_data": f"call_customer_{order.id}"
                        },
                        {
                            "text": "📞 Call Restaurant",
                            "callback_data": f"call_restaurant_{order.id}"
                        }
                    ],
                    [
                        {
                            "text": "📍 Share Live Location",
                            "callback_data": f"driver_location_{order.id}"
                        }
                    ],
                    [
                        {
                            "text": "✅ Pickup Complete",
                            "callback_data": f"pickup_complete_{order.id}"
                        }
                    ]
                ]
            }
            
            send_driver_message(driver.telegram_user_id, message, keyboard)
            
        except Exception as e:
            logger.error(f"Error notifying driver about ready delivery: {e}")
    
    def handle_order_completion(self, order):
        """Handle order completion - make driver available again"""
        try:
            if order.driver_id:
                driver = Driver.query.get(order.driver_id)
                if driver:
                    driver.is_available = True
                    db.session.commit()
                    
                    if driver.telegram_user_id:
                        message = f"✅ *Order Completed!*\n\n"
                        message += f"📋 Order #{order.id} has been delivered successfully!\n"
                        message += f"💰 You earned: {order.total_amount * 0.1:.2f} ETB (10% commission)\n\n"
                        message += f"🎯 You are now available for new orders.\n"
                        message += f"Great job! 👍"
                        
                        send_driver_message(driver.telegram_user_id, message)
                        
        except Exception as e:
            logger.error(f"Error handling order completion: {e}")

# Global instance
workflow_manager = OrderWorkflowManager()

def process_new_order(order_id):
    """Process a new order - called when customer places order"""
    try:
        # Send notification to admins first
        send_order_notification(order_id)
        
        # Note: Driver notification will be triggered when admin confirms the order
        logger.info(f"New order {order_id} processed - awaiting admin confirmation")
        
    except Exception as e:
        logger.error(f"Error processing new order {order_id}: {e}")

def handle_order_status_change(order_id, old_status, new_status):
    """Handle order status changes"""
    try:
        # Notify customer
        notify_customer_status_change(order_id, new_status)
        
        # Handle driver workflow
        workflow_manager.handle_order_status_update(order_id, old_status, new_status)
        
    except Exception as e:
        logger.error(f"Error handling status change for order {order_id}: {e}")