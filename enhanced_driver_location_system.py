"""
Enhanced Driver Location System
Implements intelligent location sharing with real-time tracking and automatic order assignment
"""

import os
import logging
import requests
import json
import threading
import time
from datetime import datetime, timedelta
from flask import request, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Driver Bot Configuration
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')

class DriverLocationTracker:
    """Manages driver location sharing and automatic order assignment"""
    
    def __init__(self):
        self.active_drivers = {}  # Track drivers with active location sharing
        self.location_history = {}  # Store location updates for each driver
        self.last_location_request = {}  # Track when we last requested location
        self.live_location_sessions = {}  # Track active live location sessions
        
    def is_driver_sharing_live_location(self, driver_telegram_id):
        """Check if driver is currently sharing live location"""
        if driver_telegram_id not in self.live_location_sessions:
            return False
            
        session = self.live_location_sessions[driver_telegram_id]
        # Check if session is still active (within last 5 minutes)
        if datetime.utcnow() - session.get('last_update', datetime.min) > timedelta(minutes=5):
            # Session expired, remove it
            del self.live_location_sessions[driver_telegram_id]
            return False
            
        return True
        
    def start_live_location_session(self, driver_telegram_id):
        """Start tracking live location session for driver"""
        self.live_location_sessions[driver_telegram_id] = {
            'started_at': datetime.utcnow(),
            'last_update': datetime.utcnow(),
            'location_count': 0
        }
        logger.info(f"Started live location session for driver {driver_telegram_id}")
        
    def update_live_location_session(self, driver_telegram_id, location):
        """Update live location session with new location"""
        if driver_telegram_id not in self.live_location_sessions:
            self.start_live_location_session(driver_telegram_id)
            
        session = self.live_location_sessions[driver_telegram_id]
        session['last_update'] = datetime.utcnow()
        session['location_count'] = session.get('location_count', 0) + 1
        session['last_location'] = location
        
        # Store in location history
        if driver_telegram_id not in self.location_history:
            self.location_history[driver_telegram_id] = []
            
        self.location_history[driver_telegram_id].append({
            'timestamp': datetime.utcnow(),
            'location': location
        })
        
        # Keep only last 50 location updates
        if len(self.location_history[driver_telegram_id]) > 50:
            self.location_history[driver_telegram_id] = self.location_history[driver_telegram_id][-50:]
            
        logger.info(f"Updated live location for driver {driver_telegram_id} (update #{session['location_count']})")
        
    def should_request_location(self, driver_telegram_id):
        """Determine if we should request location from driver"""
        # Don't request if driver is already sharing live location
        if self.is_driver_sharing_live_location(driver_telegram_id):
            return False
            
        # Don't request if we asked recently (within last 10 minutes)
        if driver_telegram_id in self.last_location_request:
            last_request = self.last_location_request[driver_telegram_id]
            if datetime.utcnow() - last_request < timedelta(minutes=10):
                return False
                
        return True
        
    def request_initial_location_sharing(self, driver_telegram_id):
        """Request driver to start sharing live location (only once)"""
        if not self.should_request_location(driver_telegram_id):
            return False
            
        self.last_location_request[driver_telegram_id] = datetime.utcnow()
        
        message = "🚗 *Welcome to ET-FOOD Driver System*\n\n"
        message += "📍 **One-time Setup Required**\n\n"
        message += "To receive delivery orders automatically, please share your live location:\n\n"
        message += "1️⃣ Tap the button below\n"
        message += "2️⃣ Select 'Share Live Location'\n"
        message += "3️⃣ Choose duration: **8 hours** (recommended)\n"
        message += "4️⃣ Tap 'Send'\n\n"
        message += "✅ **Benefits:**\n"
        message += "• Automatic order assignments\n"
        message += "• No need to manually share location again\n"
        message += "• Real-time tracking for customers\n"
        message += "• Higher delivery priority\n\n"
        message += "⚠️ **Important**: Keep live location ON during your shift!"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📍 Start Live Location Sharing",
                        "callback_data": "start_live_location"
                    }
                ],
                [
                    {
                        "text": "ℹ️ How to Share Live Location",
                        "callback_data": "location_help"
                    }
                ]
            ]
        }
        
        return self.send_driver_message(driver_telegram_id, message, keyboard=keyboard)
        
    def handle_location_update(self, driver_telegram_id, location):
        """Handle incoming location update from driver"""
        try:
            from models import Driver
            from app import db
            from main import app
            
            with app.app_context():
                driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
                if not driver:
                    logger.warning(f"Driver not found for Telegram ID: {driver_telegram_id}")
                    return False
                    
                # Update driver location in database
                driver.current_latitude = location['latitude']
                driver.current_longitude = location['longitude']
                driver.last_location_update = datetime.utcnow()
                # Activate driver when they share location
                driver.is_active = True
                db.session.commit()
                
                # Update live location session
                self.update_live_location_session(driver_telegram_id, location)
                
                # Check if this is the first location update in this session
                session = self.live_location_sessions.get(driver_telegram_id, {})
                if session.get('location_count', 0) == 1:
                    # First location update - send confirmation
                    self.send_location_confirmation(driver_telegram_id, driver.name)
                    
                    # Check for pending orders that can be assigned
                    self.check_for_pending_orders(driver_telegram_id)
                    
                logger.info(f"Location updated for driver {driver.name} (ID: {driver_telegram_id}): {location['latitude']}, {location['longitude']}")
                return True
                
        except Exception as e:
            logger.error(f"Error handling location update for {driver_telegram_id}: {e}")
            return False
            
    def send_location_confirmation(self, driver_telegram_id, driver_name):
        """Send confirmation that location sharing is active"""
        message = f"✅ **Live Location Active**\n\n"
        message += f"👋 Hi {driver_name}!\n\n"
        message += f"📍 Your live location is now being tracked\n"
        message += f"🚚 You'll automatically receive nearby delivery orders\n"
        message += f"📱 No need to share location again until you stop\n\n"
        message += f"🔄 **System Status:**\n"
        message += f"• Live tracking: **ON**\n"
        message += f"• Order assignments: **ACTIVE**\n"
        message += f"• Customer tracking: **ENABLED**\n\n"
        message += f"💡 **Tip**: Keep the app open to receive instant notifications!"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📊 View My Status",
                        "callback_data": "driver_status"
                    },
                    {
                        "text": "🎯 Ready for Orders",
                        "callback_data": "toggle_availability"
                    }
                ]
            ]
        }
        
        return self.send_driver_message(driver_telegram_id, message, keyboard=keyboard)
        
    def check_for_pending_orders(self, driver_telegram_id):
        """Check for orders that can be assigned to this driver"""
        try:
            from models import Order, Driver
            from app import db
            from main import app
            
            with app.app_context():
                # Find orders that are ready and don't have a driver assigned
                pending_orders = Order.query.filter_by(
                    status='ready',
                    driver_id=None
                ).order_by(Order.created_at.desc()).limit(3).all()
                
                if pending_orders:
                    logger.info(f"Found {len(pending_orders)} pending orders for driver {driver_telegram_id}")
                    
                    # Import the driver notification function
                    from enhanced_driver_callback_handler import notify_driver_about_orders
                    
                    for order in pending_orders:
                        # Calculate distance and notify if within range
                        if self.calculate_distance_to_order(driver_telegram_id, order) <= 10:  # 10km range
                            notify_driver_about_orders(driver_telegram_id, order.id)
                            break  # Send only one order at a time
                            
        except Exception as e:
            logger.error(f"Error checking for pending orders: {e}")
            
    def calculate_distance_to_order(self, driver_telegram_id, order):
        """Calculate distance between driver and order location"""
        try:
            from models import Driver
            from app import db
            from main import app
            
            with app.app_context():
                driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
                if not driver or not driver.current_latitude or not driver.current_longitude:
                    return float('inf')
                    
                if not order.location_lat or not order.location_lng:
                    return float('inf')
                    
                # Simple distance calculation (you can implement Haversine formula for accuracy)
                lat_diff = abs(float(driver.current_latitude) - float(order.location_lat))
                lng_diff = abs(float(driver.current_longitude) - float(order.location_lng))
                
                # Approximate distance in kilometers
                distance = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111  # 111 km per degree
                return distance
                
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return float('inf')
            
    def handle_delivery_completion(self, driver_telegram_id, order_id):
        """Handle when driver completes a delivery"""
        try:
            # Update order status
            from models import Order
            from app import db
            from main import app
            
            with app.app_context():
                order = Order.query.get(order_id)
                if order:
                    order.status = 'delivered'
                    order.updated_at = datetime.utcnow()
                    db.session.commit()
                    
                    # Send completion confirmation
                    message = f"✅ **Delivery Completed!**\n\n"
                    message += f"📦 Order #{order_id} delivered successfully\n"
                    message += f"👤 Customer: {order.customer_name}\n"
                    message += f"💰 Amount: {order.total_amount} ETB\n\n"
                    message += f"🎯 **Ready for next delivery?**\n"
                    message += f"Keep your live location active to receive new orders automatically!"
                    
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "🚚 Ready for Next Order",
                                    "callback_data": "ready_for_orders"
                                }
                            ],
                            [
                                {
                                    "text": "📊 View Earnings",
                                    "callback_data": "driver_earnings"
                                },
                                {
                                    "text": "⏸️ Take a Break",
                                    "callback_data": "toggle_availability"
                                }
                            ]
                        ]
                    }
                    
                    self.send_driver_message(driver_telegram_id, message, keyboard=keyboard)
                    
                    # Check for new orders automatically
                    self.check_for_pending_orders(driver_telegram_id)
                    
        except Exception as e:
            logger.error(f"Error handling delivery completion: {e}")
            
    def send_driver_message(self, chat_id, text, keyboard=None, parse_mode=None):
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

# Global instance
driver_location_tracker = DriverLocationTracker()