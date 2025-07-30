#!/usr/bin/env python3
"""
Trigger driver notification for Order #44 with your real Telegram ID
"""

import os
import sys
from app import app
from complete_order_workflow import OrderWorkflowManager
from models import Order, Driver

def trigger_notification():
    """Trigger driver notification for Order #44"""
    
    with app.app_context():
        print("Triggering driver notification for Order #44...")
        print("Driver with Telegram ID 383870190 should receive notification on driver bot")
        print()
        
        # Check the updated driver
        driver = Driver.query.filter_by(telegram_user_id=383870190).first()
        if driver:
            print(f"Driver found: {driver.name}")
            print(f"Telegram ID: {driver.telegram_user_id}")
            print(f"Location: {driver.current_lat}, {driver.current_lng}")
            print(f"Status: Active={driver.is_active}, Available={driver.is_available}, Approved={driver.is_approved}")
            print()
        
        # Trigger the notification
        manager = OrderWorkflowManager()
        result = manager.find_nearby_drivers(44)
        
        if result:
            print("✅ Driver notification sent!")
            print("Check your driver bot (@Food_Driver_Bot) for the delivery request!")
        else:
            print("❌ Failed to send notification")
            
        return result

if __name__ == "__main__":
    trigger_notification()