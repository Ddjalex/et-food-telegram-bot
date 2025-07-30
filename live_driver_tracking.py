#!/usr/bin/env python3
"""
Live Driver Location Tracking System
Real-time GPS tracking for delivery drivers
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from app import db
from models import Driver
from datetime import datetime, timedelta
import requests
import json

class LiveDriverTracker:
    def __init__(self):
        self.driver_bot_token = os.environ.get('DRIVER_BOT_TOKEN')
        self.base_url = f"https://api.telegram.org/bot{self.driver_bot_token}"
    
    def get_live_drivers(self):
        """Get all drivers with recent location updates"""
        with app.app_context():
            # Consider drivers active if location updated within last 10 minutes
            recent_time = datetime.utcnow() - timedelta(minutes=10)
            
            drivers = Driver.query.filter(
                Driver.is_active == True,
                Driver.is_approved == True,
                Driver.current_lat.isnot(None),
                Driver.current_lng.isnot(None),
                Driver.last_location_update >= recent_time
            ).all()
            
            return [{
                'id': driver.id,
                'name': driver.name,
                'phone': driver.phone_number,
                'telegram_id': driver.telegram_user_id,
                'vehicle_type': driver.vehicle_type,
                'is_available': driver.is_available,
                'latitude': driver.current_lat,
                'longitude': driver.current_lng,
                'last_update': driver.last_location_update.isoformat(),
                'time_ago': self.calculate_time_ago(driver.last_location_update)
            } for driver in drivers]
    
    def calculate_time_ago(self, timestamp):
        """Calculate human-readable time difference"""
        if not timestamp:
            return "Never"
        
        now = datetime.utcnow()
        diff = now - timestamp
        
        if diff.seconds < 60:
            return f"{diff.seconds} seconds ago"
        elif diff.seconds < 3600:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return f"{diff.seconds // 3600} hours ago"
    
    def request_location_from_driver(self, driver_telegram_id):
        """Request current location from specific driver"""
        message = (
            "📍 *Location Request*\n\n"
            "Please share your current location to enable order assignments.\n\n"
            "🔴 *IMPORTANT:* Tap the location button below and select 'Send Live Location' "
            "for continuous tracking during deliveries."
        )
        
        keyboard = {
            "keyboard": [[{
                "text": "📍 Share Location",
                "request_location": True
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        data = {
            'chat_id': driver_telegram_id,
            'text': message,
            'parse_mode': 'Markdown',
            'reply_markup': json.dumps(keyboard)
        }
        
        try:
            response = requests.post(f"{self.base_url}/sendMessage", data=data)
            return response.json().get('ok', False)
        except Exception as e:
            print(f"Error requesting location from driver {driver_telegram_id}: {e}")
            return False
    
    def request_live_location_from_driver(self, driver_telegram_id, duration_minutes=60):
        """Request live location sharing from driver"""
        message = (
            "🚀 *Live Location Tracking Activated*\n\n"
            "Please share your live location for real-time tracking during deliveries.\n\n"
            "📱 Instructions:\n"
            "1. Tap 'Share Live Location' below\n"
            "2. Select duration (recommended: 1 hour)\n"
            "3. Confirm to start live tracking\n\n"
            "⚡ This enables customers and admin to track your delivery progress in real-time."
        )
        
        keyboard = {
            "keyboard": [[{
                "text": "📍 Share Live Location",
                "request_location": True
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        data = {
            'chat_id': driver_telegram_id,
            'text': message,
            'parse_mode': 'Markdown',
            'reply_markup': json.dumps(keyboard)
        }
        
        try:
            response = requests.post(f"{self.base_url}/sendMessage", data=data)
            return response.json().get('ok', False)
        except Exception as e:
            print(f"Error requesting live location from driver {driver_telegram_id}: {e}")
            return False

def update_driver_location(telegram_user_id, latitude, longitude, live_period=0):
    """Update driver location in database"""
    with app.app_context():
        driver = Driver.query.filter_by(telegram_user_id=telegram_user_id).first()
        if driver:
            driver.current_lat = latitude
            driver.current_lng = longitude
            driver.last_location_update = datetime.utcnow()
            db.session.commit()
            
            print(f"✅ Updated location for {driver.name}: {latitude}, {longitude}")
            return True
        else:
            print(f"❌ Driver not found for Telegram ID: {telegram_user_id}")
            return False

def test_live_tracking():
    """Test the live tracking system"""
    tracker = LiveDriverTracker()
    
    print("Live Driver Tracking System")
    print("=" * 40)
    
    # Get live drivers
    live_drivers = tracker.get_live_drivers()
    
    if not live_drivers:
        print("❌ No drivers with recent location data found")
        
        # Get all drivers and request location
        with app.app_context():
            all_drivers = Driver.query.filter(
                Driver.is_active == True,
                Driver.is_approved == True,
                Driver.telegram_user_id.isnot(None)
            ).all()
            
            print(f"\n📍 Requesting location from {len(all_drivers)} drivers...")
            
            for driver in all_drivers:
                success = tracker.request_location_from_driver(driver.telegram_user_id)
                print(f"{'✅' if success else '❌'} Location request sent to {driver.name}")
    else:
        print(f"📍 Found {len(live_drivers)} drivers with recent location data:")
        for driver in live_drivers:
            status = "🟢 Available" if driver['is_available'] else "🔴 Busy"
            print(f"{driver['name']} - {status} - {driver['time_ago']}")
            print(f"   📍 {driver['latitude']}, {driver['longitude']}")

if __name__ == "__main__":
    test_live_tracking()