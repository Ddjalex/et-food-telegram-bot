#!/usr/bin/env python3
"""
BeUdelivery-like Driver Integration System
Comprehensive driver management with real-time notifications and advanced features
"""

import os
import json
import requests
from datetime import datetime, timedelta
from app import app
from extensions import db
from models import Driver, Order, AdminUser, SystemSettings

class DriverIntegrationSystem:
    def __init__(self):
        self.driver_bot_token = os.environ.get('DRIVER_BOT_TOKEN')
        self.base_url = f"https://api.telegram.org/bot{self.driver_bot_token}"
    
    def get_search_radius(self):
        """Get the current search radius from admin settings"""
        with app.app_context():
            setting = SystemSettings.query.filter_by(setting_key='driver_search_radius').first()
            if setting:
                try:
                    return float(setting.setting_value)
                except (ValueError, TypeError):
                    return 10.0  # Default 10km
            return 10.0  # Default 10km
        
    def send_driver_notification(self, telegram_id, message, keyboard=None):
        """Send notification to driver with enhanced formatting"""
        url = f"{self.base_url}/sendMessage"
        
        data = {
            'chat_id': telegram_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        if keyboard:
            data['reply_markup'] = json.dumps(keyboard)
        
        try:
            response = requests.post(url, data=data)
            result = response.json()
            if result.get('ok'):
                print(f"✅ Driver notification sent to {telegram_id}")
                return True
            else:
                print(f"❌ Failed to send to {telegram_id}: {result.get('description', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Error sending notification: {e}")
            return False
    
    def notify_new_order(self, order_id):
        """BeUdelivery-style order notification to nearby drivers"""
        with app.app_context():
            order = Order.query.get(order_id)
            if not order:
                return False
            
            # Find available drivers with location data (more flexible timing for testing)
            available_drivers = Driver.query.filter_by(
                is_active=True,
                is_available=True,
                is_approved=True
            ).filter(
                Driver.telegram_user_id.isnot(None),
                Driver.current_lat.isnot(None),
                Driver.current_lng.isnot(None)
            ).all()
            
            print(f"🔍 Found {len(available_drivers)} available drivers with location data")
            
            if not available_drivers:
                self.notify_admin_no_drivers(order)
                return False
            
            # Get configurable search radius
            search_radius = self.get_search_radius()
            
            # Calculate distances and sort by proximity
            drivers_with_distance = []
            for driver in available_drivers:
                # Use restaurant location as the pickup point (Addis Ababa coordinates)
                restaurant_lat, restaurant_lng = 9.047658, 38.741143
                distance = self.calculate_distance(
                    driver.current_lat, driver.current_lng,
                    restaurant_lat, restaurant_lng
                )
                if distance <= search_radius:  # Within configurable radius
                    drivers_with_distance.append((driver, distance))
            
            drivers_with_distance.sort(key=lambda x: x[1])
            
            # Send notifications to top 3 nearest drivers
            notifications_sent = 0
            failed_notifications = []
            for driver, distance in drivers_with_distance[:3]:
                print(f"🚗 Trying to notify {driver.name} (ID: {driver.telegram_user_id}) - {distance:.1f}km away")
                if self.send_order_notification(driver, order, distance):
                    notifications_sent += 1
                    print(f"✅ Successfully notified {driver.name}")
                else:
                    failed_notifications.append(f"{driver.name} (ID: {driver.telegram_user_id})")
                    print(f"❌ Failed to notify {driver.name} - they may need to start the driver bot first")
            
            if failed_notifications:
                print(f"⚠️ Failed to notify {len(failed_notifications)} drivers: {', '.join(failed_notifications)}")
                print("💡 Drivers need to start @Food_Driver_Bot first to receive notifications")
            
            print(f"📱 Sent {notifications_sent}/{len(drivers_with_distance[:3])} driver notifications for Order #{order_id} (search radius: {search_radius}km)")
            return notifications_sent > 0
    
    def send_order_notification(self, driver, order, distance):
        """Send detailed order notification to driver"""
        # Create BeUdelivery-style notification with HTML formatting
        message = f"🚚 <b>NEW DELIVERY REQUEST</b>\n\n"
        message += f"📋 <b>Order #{order.id}</b>\n"
        message += f"⏰ <b>{datetime.now().strftime('%H:%M')}</b> | 📍 <b>{distance:.1f}km away</b>\n\n"
        
        # Restaurant info
        message += f"🏪 <b>Restaurant:</b> ET-FOOD Kitchen\n"
        message += f"📍 <b>Pickup:</b> Bole Road, Addis Ababa\n\n"
        
        # Customer info 
        message += f"👤 <b>Customer:</b> {order.customer_name}\n"
        message += f"📞 <b>Phone:</b> {order.customer_phone}\n"
        message += f"🏠 <b>Delivery:</b> Location provided\n\n"
        
        # Order details
        message += f"💰 <b>Amount:</b> {order.total_amount:.2f} ETB\n"
        message += f"💳 <b>Payment:</b> {order.payment_method.upper()}\n"
        
        # Add item summary
        if order.items:
            try:
                # Parse JSON string if needed
                items = order.items if isinstance(order.items, list) else json.loads(order.items)
                item_count = sum(item.get('quantity', 1) for item in items)
                message += f"📦 <b>Items:</b> {item_count} item(s)\n"
            except (json.JSONDecodeError, TypeError):
                message += f"📦 <b>Items:</b> Multiple items\n"
        
        message += f"\n⚡ <b>FIRST TO ACCEPT GETS THE ORDER!</b>"
        
        # Create enhanced keyboard  
        from url_utils import construct_url
        webapp_url = construct_url(f"/driver-panel?order_id={order.id}&driver_id={driver.id}")
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ ACCEPT ORDER",
                        "callback_data": f"driver_accept_{order.id}"
                    },
                    {
                        "text": "❌ DECLINE",
                        "callback_data": f"driver_reject_{order.id}"
                    }
                ],
                [
                    {
                        "text": "📱 View Full Details",
                        "web_app": {"url": webapp_url}
                    }
                ],
                [
                    {
                        "text": "📞 Restaurant Info",
                        "callback_data": f"restaurant_info_{order.id}"
                    },
                    {
                        "text": "📞 Customer Info",
                        "callback_data": f"customer_info_{order.id}"
                    }
                ],
                [
                    {
                        "text": "📍 View Location",
                        "callback_data": f"view_location_{order.id}"
                    }
                ]
            ]
        }
        
        return self.send_driver_notification(driver.telegram_user_id, message, keyboard)
    
    def notify_admin_no_drivers(self, order):
        """Notify admin when no drivers are available"""
        search_radius = self.get_search_radius()
        admin_message = f"⚠️ *NO DRIVERS AVAILABLE*\n\n"
        admin_message += f"Order #{order.id} cannot be assigned\n"
        admin_message += f"Customer: {order.customer_name}\n"
        admin_message += f"Phone: {order.customer_phone}\n"
        admin_message += f"Amount: {order.total_amount:.2f} ETB\n"
        admin_message += f"Search Radius: {search_radius}km\n\n"
        admin_message += f"*Action Required:*\n"
        admin_message += f"• Contact drivers to go online\n"
        admin_message += f"• Manually assign from admin dashboard\n"
        admin_message += f"• Consider increasing search radius\n"
        admin_message += f"• Consider using delivery bot"
        
        # Send to all active admins
        admins = AdminUser.query.filter_by(is_active=True).all()
        for admin in admins:
            self.send_driver_notification(admin.telegram_user_id, admin_message)
    
    def calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two coordinates"""
        import math
        R = 6371  # Earth's radius in km
        dLat = math.radians(lat2 - lat1)
        dLng = math.radians(lng2 - lng1)
        a = (math.sin(dLat/2) * math.sin(dLat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dLng/2) * math.sin(dLng/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def handle_driver_acceptance(self, driver_telegram_id, order_id):
        """Handle when driver accepts an order"""
        with app.app_context():
            driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
            order = Order.query.get(order_id)
            
            if not driver or not order:
                return False
            
            # Check if order is still available
            if order.driver_id:
                self.send_driver_notification(
                    driver_telegram_id,
                    f"❌ *Order #{order_id} Already Assigned*\n\nSorry, another driver already accepted this order. Keep your app active for the next opportunity!"
                )
                return False
            
            # Assign order to driver
            order.driver_id = driver.id
            order.status = 'confirmed'
            driver.is_available = False
            db.session.commit()
            
            # Send confirmation to driver
            confirmation_message = f"🎉 *ORDER ACCEPTED SUCCESSFULLY!*\n\n"
            confirmation_message += f"📋 *Order #{order_id}*\n"
            confirmation_message += f"👤 Customer: {order.customer_name}\n"
            confirmation_message += f"📞 Phone: {order.customer_phone}\n"
            confirmation_message += f"🏠 Address: {order.customer_address}\n"
            confirmation_message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
            confirmation_message += f"📍 *Next Steps:*\n"
            confirmation_message += f"1. Go to ET-FOOD Kitchen for pickup\n"
            confirmation_message += f"2. Share your live location\n"
            confirmation_message += f"3. Update order status when ready\n\n"
            confirmation_message += f"💪 *Good luck with your delivery!*"
            
            pickup_keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📍 Share Live Location",
                            "callback_data": f"share_location_{order_id}"
                        }
                    ],
                    [
                        {
                            "text": "🍽️ Picked Up - On The Way",
                            "callback_data": f"pickup_complete_{order_id}"
                        }
                    ],
                    [
                        {
                            "text": "📱 Open Driver Panel",
                            "web_app": {"url": f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/driver-panel?order_id={order_id}&driver_id={driver.id}"}
                        }
                    ]
                ]
            }
            
            self.send_driver_notification(driver_telegram_id, confirmation_message, pickup_keyboard)
            
            # Notify customer
            self.notify_customer_assignment(order, driver)
            
            # Notify admin
            self.notify_admin_assignment(order, driver)
            
            return True
    
    def notify_customer_assignment(self, order, driver):
        """Notify customer that driver has been assigned"""
        from bot_minimal import send_message
        
        customer_message = f"🚚 *Driver Assigned to Your Order!*\n\n"
        customer_message += f"📋 Order #{order.id}\n"
        customer_message += f"👤 Driver: {driver.name}\n"
        customer_message += f"📞 Phone: {driver.phone_number}\n"
        customer_message += f"🚗 Vehicle: {driver.vehicle_type.title()}\n\n"
        customer_message += f"📍 Your driver is on the way to pick up your order!\n"
        customer_message += f"⏱️ Estimated delivery: 20-30 minutes\n\n"
        customer_message += f"You can track your order in real-time."
        
        send_message(order.telegram_user_id, customer_message, parse_mode='Markdown')
    
    def notify_admin_assignment(self, order, driver):
        """Notify admin about successful driver assignment"""
        admin_message = f"✅ *ORDER ASSIGNED SUCCESSFULLY*\n\n"
        admin_message += f"📋 Order #{order.id}\n"
        admin_message += f"👤 Driver: {driver.name}\n"
        admin_message += f"📞 Driver Phone: {driver.phone_number}\n"
        admin_message += f"👤 Customer: {order.customer_name}\n"
        admin_message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
        admin_message += f"🎯 *Status:* Driver accepted and is heading to pickup"
        
        # Send to all active admins
        admins = AdminUser.query.filter_by(is_active=True).all()
        for admin in admins:
            self.send_driver_notification(admin.telegram_user_id, admin_message)

# Initialize the system
driver_system = DriverIntegrationSystem()

def test_driver_integration():
    """Test the BeUdelivery-like driver integration"""
    print("🚀 Testing BeUdelivery-like Driver Integration System")
    
    # Test with a recent order
    with app.app_context():
        latest_order = Order.query.order_by(Order.id.desc()).first()
        if latest_order:
            print(f"📋 Testing with Order #{latest_order.id}")
            success = driver_system.notify_new_order(latest_order.id)
            print(f"✅ Notification sent: {success}")
        else:
            print("❌ No orders found to test")

if __name__ == "__main__":
    test_driver_integration()