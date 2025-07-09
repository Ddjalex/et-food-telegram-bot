"""
Driver Registration System
Handles new driver registration flow with document upload
"""

import os
import logging
import requests
import json
from datetime import datetime
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Driver Bot Configuration
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')

def send_driver_message(chat_id, text, keyboard=None, parse_mode=None):
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
        else:
            logger.error(f"Failed to send message: {response.text}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")

def start_driver_registration(chat_id):
    """Start driver registration flow"""
    message = "📋 *Driver Registration*\n\n"
    message += "Welcome to ET-FOOD driver registration!\n\n"
    message += "📝 **Step 1: Share Your Contact**\n"
    message += "We need your phone number to create your driver profile.\n\n"
    message += "👇 Please share your contact information:"
    
    keyboard = {
        "keyboard": [
            [
                {
                    "text": "📞 Share My Contact",
                    "request_contact": True
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_contact_request_for_registration(chat_id):
    """Send contact request for driver registration"""
    message = "📞 *Share Your Contact*\n\n"
    message += "Please share your phone number to continue with registration.\n\n"
    message += "👇 Tap the button below to share your contact:"
    
    keyboard = {
        "keyboard": [
            [
                {
                    "text": "📞 Share My Contact",
                    "request_contact": True
                }
            ]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def handle_driver_contact_registration(chat_id, contact, user_data):
    """Handle contact sharing for driver registration"""
    try:
        # Extract user information
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()
        phone_number = contact.get('phone_number', '')
        
        # Create registration web app URL
        webapp_url = f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/driver-registration"
        webapp_url += f"?telegram_id={chat_id}"
        webapp_url += f"&name={full_name}"
        webapp_url += f"&phone={phone_number}"
        
        message = "✅ *Contact Received!*\n\n"
        message += f"📱 Name: {full_name}\n"
        message += f"📞 Phone: {phone_number}\n\n"
        message += "📝 **Step 2: Complete Registration**\n"
        message += "Please fill out the registration form and upload required documents.\n\n"
        message += "👇 Click the button below to open the registration form:"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📝 Complete Registration",
                        "web_app": {"url": webapp_url}
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error handling driver contact registration: {e}")

def send_driver_registration_pending(chat_id, driver_name):
    """Send registration pending message"""
    message = f"⏳ *Registration Submitted*\n\n"
    message += f"Thank you, {driver_name}!\n\n"
    message += f"📋 Your driver registration has been submitted successfully.\n"
    message += f"📄 All required documents have been uploaded.\n\n"
    message += f"⏰ **What's Next?**\n"
    message += f"• Admin will review your application\n"
    message += f"• Document verification process\n"
    message += f"• You'll receive notification when approved\n\n"
    message += f"📞 Contact support if you have any questions."
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📞 Contact Support",
                    "callback_data": "contact_support"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def send_driver_approval_notification(chat_id, driver_name):
    """Send driver approval notification"""
    message = f"🎉 *Congratulations, {driver_name}!*\n\n"
    message += f"✅ Your driver registration has been **APPROVED**!\n\n"
    message += f"🚚 **You're now part of the ET-FOOD delivery team!**\n\n"
    message += f"📋 **Next Steps:**\n"
    message += f"• View available orders\n"
    message += f"• Share your location to receive assignments\n"
    message += f"• Start earning with deliveries\n\n"
    message += f"👇 Click below to access your driver dashboard:"
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📋 View Orders",
                    "web_app": {"url": f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}/driver-panel?driver_id={chat_id}"}
                }
            ],
            [
                {
                    "text": "📍 Share Location",
                    "callback_data": "request_location"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard)

def notify_admin_driver_registration(driver_data):
    """Notify admin about new driver registration"""
    from bot_minimal import send_message_to_admin
    from models import AdminUser
    
    try:
        # Send notification to all admins
        admins = AdminUser.query.filter_by(is_active=True).all()
        
        message = f"👤 *New Driver Registration*\n\n"
        message += f"📝 Name: {driver_data['name']}\n"
        message += f"📞 Phone: {driver_data['phone_number']}\n"
        message += f"🚗 Vehicle: {driver_data['vehicle_type']}\n"
        message += f"📄 Documents: {'✅ Uploaded' if driver_data.get('documents_uploaded') else '❌ Missing'}\n"
        message += f"📅 Registered: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        message += f"🔍 Please review the registration and approve or reject."
        
        for admin in admins:
            send_message_to_admin(admin.telegram_user_id, message)
            
    except Exception as e:
        logger.error(f"Error notifying admin about driver registration: {e}")