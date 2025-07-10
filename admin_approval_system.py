#!/usr/bin/env python3
"""
Admin Approval System for Driver Registration
"""

import os
import sys
from app import app
from extensions import db
from models import Driver, AdminUser
from bot_minimal import send_message_to_admin
from driver_bot import send_driver_message

def approve_driver(driver_id, admin_telegram_id):
    """Approve a pending driver"""
    
    with app.app_context():
        driver = Driver.query.get(driver_id)
        if not driver:
            return False, "Driver not found"
            
        if driver.approval_status != 'pending':
            return False, f"Driver is already {driver.approval_status}"
            
        # Update driver status
        driver.approval_status = 'approved'
        driver.is_approved = True
        driver.is_available = True
        driver.approved_by = admin_telegram_id
        driver.approved_at = db.func.now()
        
        db.session.commit()
        
        # Send approval notification to driver
        send_driver_approval_notification(driver.telegram_user_id, driver.name)
        
        # Send confirmation to admin
        send_message_to_admin(admin_telegram_id, 
            f"✅ Driver {driver.name} has been approved and is now available for deliveries.")
        
        return True, f"Driver {driver.name} approved successfully"

def reject_driver(driver_id, admin_telegram_id, reason="Application does not meet requirements"):
    """Reject a pending driver"""
    
    with app.app_context():
        driver = Driver.query.get(driver_id)
        if not driver:
            return False, "Driver not found"
            
        if driver.approval_status != 'pending':
            return False, f"Driver is already {driver.approval_status}"
            
        # Update driver status
        driver.approval_status = 'rejected'
        driver.is_approved = False
        driver.is_available = False
        driver.rejection_reason = reason
        
        db.session.commit()
        
        # Send rejection notification to driver
        send_driver_rejection_notification(driver.telegram_user_id, driver.name, reason)
        
        # Send confirmation to admin
        send_message_to_admin(admin_telegram_id, 
            f"❌ Driver {driver.name} has been rejected. Reason: {reason}")
        
        return True, f"Driver {driver.name} rejected"

def send_driver_approval_notification(chat_id, driver_name):
    """Send driver approval notification with mandatory location sharing"""
    message = f"🎉 *Congratulations {driver_name}!*\n\n"
    message += f"✅ Your driver registration has been **APPROVED**!\n\n"
    message += f"🚗 You are now an official ET-FOOD delivery driver.\n"
    message += f"💰 You can start earning money right away!\n\n"
    message += f"📍 **IMPORTANT - Location Sharing Required:**\n"
    message += f"To receive delivery requests, you must share your live location.\n"
    message += f"This helps us assign orders to the nearest available drivers.\n\n"
    message += f"📱 **Driver Commands:**\n"
    message += f"• /status - Check your status\n"
    message += f"• /toggle - Toggle availability\n"
    message += f"• /orders - View your orders\n"
    message += f"• /earnings - Check earnings\n\n"
    message += f"🎯 **Ready to start delivering?**\n"
    message += f"👇 **First, share your location below:**"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📍 Share Live Location (Required)",
                    "callback_data": "driver_share_location_required"
                }
            ],
            [
                {
                    "text": "📊 My Status", 
                    "callback_data": "driver_status"
                },
                {
                    "text": "❓ Help",
                    "callback_data": "driver_help"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_driver_rejection_notification(chat_id, driver_name, reason):
    """Send driver rejection notification"""
    message = f"❌ *Registration Update*\n\n"
    message += f"Unfortunately, your driver registration has been declined.\n\n"
    message += f"**Reason:** {reason}\n\n"
    message += f"📞 If you have questions, please contact our support team.\n"
    message += f"🔄 You can reapply after addressing the concerns mentioned above."
    
    send_driver_message(chat_id, message)

def get_pending_drivers_for_admin():
    """Get list of pending drivers for admin approval"""
    
    with app.app_context():
        pending_drivers = Driver.query.filter_by(approval_status='pending').all()
        
        if not pending_drivers:
            return "📋 No pending driver registrations."
            
        message = f"📋 *Pending Driver Registrations* ({len(pending_drivers)})\n\n"
        
        for driver in pending_drivers:
            message += f"👤 **{driver.name}**\n"
            message += f"📞 Phone: {driver.phone_number}\n"
            message += f"🚗 Vehicle: {driver.vehicle_type}\n"
            message += f"🆔 Telegram: {driver.telegram_user_id}\n"
            message += f"📅 Applied: {driver.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            message += f"━━━━━━━━━━━━━━━━━━\n"
        
        message += f"\n💡 Use admin panel to approve/reject drivers."
        
        return message

if __name__ == "__main__":
    # Test the approval system
    print(get_pending_drivers_for_admin())