"""
Enhanced Order Flow System
Handles complete customer information delivery to drivers when they accept orders
"""

import os
import logging
import json
from datetime import datetime
from models import Order, Driver, AdminUser
from extensions import db
from driver_bot import send_driver_message

logger = logging.getLogger(__name__)

def handle_driver_order_acceptance(driver_telegram_id, order_id):
    """Handle driver order acceptance with complete customer information delivery"""
    try:
        from app import app
        
        with app.app_context():
            # Find driver
            driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
            if not driver:
                logger.error(f"Driver with telegram_id {driver_telegram_id} not found")
                return False
                
            # Find order
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
                
            # Check if order is still available
            if order.status != 'confirmed':
                logger.error(f"Order {order_id} is not confirmed (status: {order.status})")
                return False
                
            # Assign driver to order
            order.driver_id = driver.id
            order.status = 'assigned'
            order.assigned_at = datetime.utcnow()
            
            # Update driver availability
            driver.is_available = False
            driver.current_order_id = order_id
            
            db.session.commit()
            
            # Send complete customer information to driver
            send_complete_customer_info_to_driver(driver_telegram_id, order_id)
            
            # Notify customer about driver assignment
            notify_customer_about_driver_assignment(order_id, driver.name)
            
            # Notify admin about successful assignment
            notify_admin_about_driver_assignment(order_id, driver.name)
            
            logger.info(f"Order {order_id} successfully assigned to driver {driver.name}")
            return True
            
    except Exception as e:
        logger.error(f"Error handling driver order acceptance: {e}")
        return False

def send_complete_customer_info_to_driver(driver_telegram_id, order_id):
    """Send complete customer information to driver"""
    try:
        from app import app
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
                
            driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
            if not driver:
                logger.error(f"Driver with telegram_id {driver_telegram_id} not found")
                return False
            
            # Parse order items
            items_list = []
            if order.items:
                try:
                    items_data = json.loads(order.items)
                    for item in items_data:
                        items_list.append(f"• {item['name']} x{item['quantity']} - {item['price']:.2f} ETB")
                except json.JSONDecodeError:
                    items_list.append("• Order items (details unavailable)")
            
            # Create comprehensive message with all customer information
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
            
            # Add GPS coordinates if available
            if order.location_lat and order.location_lng:
                message += f"• GPS: {order.location_lat:.6f}, {order.location_lng:.6f}\n"
            
            message += f"\n🛒 **Order Items:**\n"
            if items_list:
                message += "\n".join(items_list)
            else:
                message += "• Details will be provided at pickup\n"
            
            message += f"\n🏪 **Restaurant Information:**\n"
            message += f"• Name: ET-FOOD Kitchen\n"
            message += f"• Phone: +251-911-123-456\n"
            message += f"• Address: Main Street, Addis Ababa\n\n"
            
            message += f"📝 **Instructions:**\n"
            message += f"1. Call restaurant to confirm order ready\n"
            message += f"2. Pick up order from restaurant\n"
            message += f"3. Contact customer before delivery\n"
            message += f"4. Share live location during delivery\n"
            message += f"5. Confirm delivery completion\n\n"
            
            message += f"🚚 **Ready to start delivery?**"
            
            # Create comprehensive action keyboard
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📞 Call Customer",
                            "url": f"tel:{order.customer_phone}"
                        },
                        {
                            "text": "📞 Call Restaurant",
                            "url": "tel:+251911123456"
                        }
                    ],
                    [
                        {
                            "text": "🗺️ Open Customer Location",
                            "url": f"https://maps.google.com/?q={order.location_lat},{order.location_lng}" if order.location_lat and order.location_lng else "https://maps.google.com/?q=addis+ababa"
                        }
                    ],
                    [
                        {
                            "text": "📍 Share Live Location",
                            "callback_data": f"share_live_location_{order_id}"
                        }
                    ],
                    [
                        {
                            "text": "✅ Picked Up Order",
                            "callback_data": f"pickup_complete_{order_id}"
                        },
                        {
                            "text": "🏁 Delivery Complete",
                            "callback_data": f"delivery_complete_{order_id}"
                        }
                    ]
                ]
            }
            
            # Send the comprehensive message
            send_driver_message(driver_telegram_id, message, keyboard)
            
            logger.info(f"Complete customer information sent to driver {driver.name} for order {order_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error sending complete customer info: {e}")
        return False

def notify_customer_about_driver_assignment(order_id, driver_name):
    """Notify customer about driver assignment"""
    try:
        from app import app
        from bot_minimal import send_message
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            driver = Driver.query.filter_by(name=driver_name).first()
            if not driver:
                logger.error(f"Driver {driver_name} not found")
                return False
            
            # Create customer notification message
            message = f"🚚 *Driver Assigned to Your Order!*\n\n"
            message += f"📋 Order #{order_id}\n"
            message += f"👤 Driver: {driver.name}\n"
            message += f"📞 Driver Phone: {driver.phone_number}\n"
            message += f"🚗 Vehicle: {driver.vehicle_type.title()}\n\n"
            message += f"⏰ **Estimated Delivery Time:** 30-45 minutes\n"
            message += f"📱 Your driver will contact you shortly\n\n"
            message += f"🔔 **You will receive updates when:**\n"
            message += f"• Driver picks up your order\n"
            message += f"• Driver is on the way\n"
            message += f"• Order is delivered\n\n"
            message += f"📞 Need help? Contact ET-FOOD: +251-911-123-456"
            
            # Send notification to customer
            send_message(order.telegram_user_id, message)
            
            logger.info(f"Customer notification sent for order {order_id} assignment to {driver_name}")
            return True
            
    except Exception as e:
        logger.error(f"Error notifying customer about driver assignment: {e}")
        return False

def notify_admin_about_driver_assignment(order_id, driver_name):
    """Notify admin about successful driver assignment"""
    try:
        from app import app
        from bot_minimal import send_message_to_admin
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            # Create admin notification message
            message = f"✅ *Driver Assignment Successful*\n\n"
            message += f"📋 Order #{order_id}\n"
            message += f"👤 Driver: {driver_name}\n"
            message += f"👤 Customer: {order.customer_name}\n"
            message += f"📞 Customer Phone: {order.customer_phone}\n"
            message += f"💰 Order Value: {order.total_amount:.2f} ETB\n"
            message += f"🕐 Assignment Time: {datetime.now().strftime('%I:%M %p')}\n\n"
            message += f"🎯 **Order Status:** ASSIGNED\n"
            message += f"🚚 Driver has received complete customer information\n"
            message += f"📱 Monitor delivery progress in admin dashboard"
            
            # Send to all admins
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                if admin.telegram_user_id:
                    send_message_to_admin(admin.telegram_user_id, message)
            
            logger.info(f"Admin notification sent for order {order_id} assignment to {driver_name}")
            return True
            
    except Exception as e:
        logger.error(f"Error notifying admin about driver assignment: {e}")
        return False

def handle_pickup_completion(driver_telegram_id, order_id):
    """Handle pickup completion notification"""
    try:
        from app import app
        from bot_minimal import send_message
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
            if not driver:
                logger.error(f"Driver with telegram_id {driver_telegram_id} not found")
                return False
            
            # Update order status
            order.status = 'out_for_delivery'
            order.picked_up_at = datetime.utcnow()
            
            db.session.commit()
            
            # Notify customer
            customer_message = f"🚚 *Order Picked Up!*\n\n"
            customer_message += f"📋 Order #{order_id}\n"
            customer_message += f"👤 Driver: {driver.name}\n"
            customer_message += f"📞 Driver Phone: {driver.phone_number}\n\n"
            customer_message += f"🛣️ Your order is now on the way!\n"
            customer_message += f"⏰ Estimated delivery: 15-30 minutes\n"
            customer_message += f"📱 Your driver will contact you upon arrival"
            
            send_message(order.telegram_user_id, customer_message)
            
            # Confirm to driver
            driver_message = f"✅ *Pickup Confirmed*\n\n"
            driver_message += f"📋 Order #{order_id} marked as picked up\n"
            driver_message += f"🛣️ Please proceed to delivery location\n"
            driver_message += f"📞 Contact customer: {order.customer_phone}\n"
            driver_message += f"📍 Address: {order.customer_address}\n\n"
            driver_message += f"🚚 Safe driving!"
            
            send_driver_message(driver_telegram_id, driver_message)
            
            logger.info(f"Pickup completion handled for order {order_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error handling pickup completion: {e}")
        return False

def handle_delivery_completion(driver_telegram_id, order_id):
    """Handle delivery completion"""
    try:
        from app import app
        from bot_minimal import send_message
        
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return False
            
            driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
            if not driver:
                logger.error(f"Driver with telegram_id {driver_telegram_id} not found")
                return False
            
            # Update order status
            order.status = 'delivered'
            order.delivered_at = datetime.utcnow()
            
            # Make driver available again
            driver.is_available = True
            driver.current_order_id = None
            
            db.session.commit()
            
            # Notify customer
            customer_message = f"🎉 *Order Delivered!*\n\n"
            customer_message += f"📋 Order #{order_id}\n"
            customer_message += f"✅ Successfully delivered by {driver.name}\n"
            customer_message += f"🕐 Delivery time: {order.delivered_at.strftime('%I:%M %p')}\n\n"
            customer_message += f"🙏 Thank you for choosing ET-FOOD!\n"
            customer_message += f"⭐ Rate your experience: /feedback\n"
            customer_message += f"🍽️ Order again: /menu"
            
            send_message(order.telegram_user_id, customer_message)
            
            # Confirm to driver
            driver_message = f"🎉 *Delivery Completed!*\n\n"
            driver_message += f"📋 Order #{order_id} marked as delivered\n"
            driver_message += f"✅ You are now available for new orders\n"
            driver_message += f"💰 Earnings updated in your account\n\n"
            driver_message += f"🚚 Great job! Ready for the next delivery?"
            
            send_driver_message(driver_telegram_id, driver_message)
            
            logger.info(f"Delivery completion handled for order {order_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error handling delivery completion: {e}")
        return False

def test_enhanced_order_flow():
    """Test the enhanced order flow system"""
    try:
        from app import app
        
        with app.app_context():
            # Find a confirmed order
            order = Order.query.filter_by(status='confirmed').first()
            if not order:
                logger.warning("No confirmed orders found for testing")
                return False
            
            # Find an available driver
            driver = Driver.query.filter_by(is_available=True, is_approved=True).first()
            if not driver:
                logger.warning("No available drivers found for testing")
                return False
            
            logger.info(f"Testing enhanced order flow with Order #{order.id} and Driver {driver.name}")
            
            # Test complete order acceptance
            result = handle_driver_order_acceptance(driver.telegram_user_id, order.id)
            
            if result:
                logger.info("✅ Enhanced order flow test successful")
                return True
            else:
                logger.error("❌ Enhanced order flow test failed")
                return False
                
    except Exception as e:
        logger.error(f"Error testing enhanced order flow: {e}")
        return False

if __name__ == "__main__":
    # Test the enhanced order flow
    test_enhanced_order_flow()