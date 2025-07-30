"""
Manual Driver Assignment System
Handles manual driver assignment workflow replacing automatic notifications
"""

import logging
from datetime import datetime, timedelta
from models import Order, Driver, AdminUser
from app import db
from bot_minimal import send_message_to_admin

logger = logging.getLogger(__name__)

def process_new_order(order_id):
    """Process a new order - NO automatic driver notification"""
    try:
        from bot_minimal import send_order_notification
        
        # Send notification to admins only - NO automatic driver notification
        send_order_notification(order_id)
        
        logger.info(f"New order {order_id} processed - admin must manually confirm to notify drivers")
        
    except Exception as e:
        logger.error(f"Error processing new order {order_id}: {e}")

def get_available_drivers_for_order(order_id):
    """Get list of available drivers for manual assignment"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return []
        
        # Get all available drivers
        available_drivers = Driver.query.filter_by(
            is_active=True,
            is_available=True,
            approval_status='approved'
        ).all()
        
        driver_list = []
        for driver in available_drivers:
            driver_info = {
                'id': driver.id,
                'name': driver.name,
                'phone_number': driver.phone_number,
                'vehicle_type': driver.vehicle_type,
                'telegram_user_id': driver.telegram_user_id,
                'has_location': driver.current_lat is not None and driver.current_lng is not None,
                'last_location_update': driver.last_location_update.isoformat() if driver.last_location_update else None,
                'distance_km': None
            }
            
            # Calculate distance if both order and driver have coordinates
            if (order.location_lat and order.location_lng and 
                driver.current_lat and driver.current_lng):
                from complete_order_workflow import calculate_distance
                distance = calculate_distance(
                    order.location_lat, order.location_lng,
                    driver.current_lat, driver.current_lng
                )
                driver_info['distance_km'] = round(distance, 2)
            
            driver_list.append(driver_info)
        
        # Sort by distance if available, otherwise by name
        driver_list.sort(key=lambda x: (x['distance_km'] or 999, x['name']))
        
        return driver_list
        
    except Exception as e:
        logger.error(f"Error getting available drivers for order {order_id}: {e}")
        return []

def manually_assign_driver(order_id, driver_id, admin_telegram_id):
    """Manually assign a driver to an order"""
    try:
        order = Order.query.get(order_id)
        driver = Driver.query.get(driver_id)
        
        if not order or not driver:
            return {'success': False, 'message': 'Order or driver not found'}
        
        if order.driver_id:
            return {'success': False, 'message': 'Order already has a driver assigned'}
        
        if not driver.is_available:
            return {'success': False, 'message': 'Driver is not available'}
        
        # Assign driver to order
        order.driver_id = driver_id
        # Only update status if it's pending, otherwise keep current status
        if order.status == 'pending':
            order.status = 'confirmed'
        order.assigned_at = datetime.utcnow()
        
        # Make driver busy
        driver.is_available = False
        
        db.session.commit()
        
        # Notify driver about assignment
        notify_driver_assignment(driver, order)
        
        # Notify admin about successful assignment
        if admin_telegram_id:
            send_message_to_admin(admin_telegram_id, 
                f"✅ Driver {driver.name} assigned to Order #{order_id}")
        
        logger.info(f"Order {order_id} manually assigned to driver {driver.name} by admin")
        
        return {
            'success': True, 
            'message': f'Driver {driver.name} assigned successfully',
            'driver_name': driver.name,
            'order_id': order_id
        }
        
    except Exception as e:
        logger.error(f"Error manually assigning driver: {e}")
        return {'success': False, 'message': 'Assignment failed'}

def notify_driver_assignment(driver, order):
    """Notify driver about manual assignment"""
    try:
        from driver_bot import send_driver_message
        
        if not driver.telegram_user_id:
            logger.warning(f"Driver {driver.name} has no telegram_user_id")
            return
        
        message = f"🚗 *NEW DELIVERY ASSIGNMENT*\n\n"
        message += f"📋 Order #{order.id}\n\n"
        
        message += f"👤 **Customer Details:**\n"
        message += f"• Name: {order.customer_name}\n"
        message += f"• Phone: {order.customer_phone}\n"
        message += f"• Address: {order.customer_address}\n\n"
        
        # Add distance if available
        if (order.location_lat and order.location_lng and 
            driver.current_lat and driver.current_lng):
            from complete_order_workflow import calculate_distance
            distance = calculate_distance(
                order.location_lat, order.location_lng,
                driver.current_lat, driver.current_lng
            )
            message += f"📍 Distance: {distance:.2f} km\n\n"
        
        message += f"🎯 **You have been assigned this delivery!**\n"
        message += f"Please confirm acceptance or contact restaurant for details."
        
        # Create keyboard for driver actions
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Accept Order",
                        "callback_data": f"accept_order_{order.id}"
                    },
                    {
                        "text": "❌ Reject Order",
                        "callback_data": f"reject_order_{order.id}"
                    }
                ],
                [
                    {
                        "text": "📞 Call Customer",
                        "url": f"tel:{order.customer_phone}"
                    },
                    {
                        "text": "📞 Call Restaurant",
                        "url": f"tel:+251911123456"
                    }
                ]
            ]
        }
        
        send_driver_message(driver.telegram_user_id, message, keyboard)
        logger.info(f"Manual assignment notification sent to driver {driver.name}")
        
    except Exception as e:
        logger.error(f"Error notifying driver about assignment: {e}")

def send_manual_assignment_options(admin_telegram_id, order_id):
    """Send manual assignment options to admin"""
    try:
        available_drivers = get_available_drivers_for_order(order_id)
        
        if not available_drivers:
            send_message_to_admin(admin_telegram_id, 
                "⚠️ No available drivers found for manual assignment")
            return
        
        message = f"🚗 *MANUAL DRIVER ASSIGNMENT*\n\n"
        message += f"📋 Order #{order_id}\n"
        message += f"Available Drivers ({len(available_drivers)}):\n\n"
        
        for i, driver in enumerate(available_drivers[:5], 1):  # Show max 5 drivers
            message += f"{i}. {driver['name']}\n"
            message += f"   📱 {driver['phone_number']}\n"
            message += f"   🚲 {driver['vehicle_type']}\n"
            if driver['distance_km']:
                message += f"   📍 {driver['distance_km']} km away\n"
            message += f"   🕐 Location: {driver['last_location_update'][:16] if driver['last_location_update'] else 'No data'}\n\n"
        
        message += f"Use admin dashboard to assign drivers manually."
        
        send_message_to_admin(admin_telegram_id, message)
        
    except Exception as e:
        logger.error(f"Error sending manual assignment options: {e}")