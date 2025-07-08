#!/usr/bin/env python3
"""
Test script to verify driver bot functionality
"""

import os
import requests
import json

DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')

def test_driver_bot():
    """Test driver bot basic functionality"""
    
    if not DRIVER_BOT_TOKEN:
        print("❌ DRIVER_BOT_TOKEN not found in environment")
        return False
    
    # Test 1: Check bot info
    print("🔍 Testing driver bot connection...")
    url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/getMe"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get('ok'):
            bot_info = data.get('result', {})
            print(f"✅ Driver bot connected successfully!")
            print(f"   Bot name: {bot_info.get('first_name', 'Unknown')}")
            print(f"   Username: @{bot_info.get('username', 'No username')}")
            print(f"   Bot ID: {bot_info.get('id', 'Unknown')}")
        else:
            print(f"❌ Bot connection failed: {data}")
            return False
            
    except Exception as e:
        print(f"❌ Error connecting to bot: {e}")
        return False
    
    # Test 2: Check webhook status
    print("\n🔍 Testing webhook configuration...")
    webhook_url = f"https://api.telegram.org/bot{DRIVER_BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(webhook_url)
        webhook_data = response.json()
        
        if webhook_data.get('ok'):
            webhook_info = webhook_data.get('result', {})
            current_webhook = webhook_info.get('url', '')
            
            if current_webhook:
                print(f"✅ Webhook configured: {current_webhook}")
                print(f"   Last error: {webhook_info.get('last_error_message', 'None')}")
            else:
                print("⚠️  No webhook configured")
        else:
            print(f"❌ Webhook check failed: {webhook_data}")
            
    except Exception as e:
        print(f"❌ Error checking webhook: {e}")
    
    print("\n✅ Driver bot test completed!")
    print("\nTo test the bot:")
    print("1. Find your driver bot in Telegram")
    print("2. Send /start command")
    print("3. Bot should respond with welcome message")
    
    return True

if __name__ == "__main__":
    test_driver_bot()