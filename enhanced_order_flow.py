#!/usr/bin/env python3
"""
Enhanced Order Flow: Client Order → Admin Confirm → Find Drivers → Driver Accept → Send All Info
"""

import os
import sys
from datetime import datetime
from app import app
from extensions import db
from models import Order, Driver
from complete_order_workflow import OrderWorkflowManager
from driver_bot import send_driver_message

def handle_driver_order_acceptance(driver_telegram_id, order_id):
    """Handle when driver accepts order and send complete client information"""
    
    with app.app_context():
        # Find the driver and order
        driver = Driver.query.filter_by(telegram_user_id=driver_telegram_id).first()
        order = Order.query.get(order_id)
        
        if not driver or not order:
            return False, "Driver or order not found"
            
        if order.driver_id:
            return False, "Order already assigned to another driver"
            
        # Assign order to driver
        order.driver_id = driver.id
        order.status = 'assigned'
        order.updated_at = datetime.utcnow()
        
        # Make driver unavailable for other orders
        driver.is_available = False
        
        db.session.commit()
        
        # Send complete order information to driver
        send_complete_order_info_to_driver(driver_telegram_id, order)
        
        # Notify admin about assignment
        from bot_minimal import send_message_to_admin
        send_message_to_admin(383870190, 
            f"✅ Order #{order_id} assigned to {driver.name}")
        
        # Notify customer about driver assignment
        notify_customer_driver_assigned(order, driver)
        
        return True, f"Order assigned to {driver.name}"

def send_complete_order_info_to_driver(driver_telegram_id, order):
    """Send complete client order information to driver"""
    
    # Format order items
    items_text = ""
    for item in order.items:
        items_text += f"• {item['name']} x{item['quantity']} - {item['total']} ETB\n"
    
    # Create comprehensive order message
    message = f"🎯 *ORDER CONFIRMED & ASSIGNED TO YOU*\n\n"
    message += f"📋 **Order #{order.id}**\n"
    message += f"🕐 Ordered: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    message += f"👤 **CUSTOMER INFORMATION**\n"
    message += f"📱 Name: {order.customer_name}\n"
    message += f"📞 Phone: {order.customer_phone}\n"
    message += f"📍 Address: {order.customer_address}\n"
    if order.location_lat and order.location_lng:
        message += f"🗺️ GPS: {order.location_lat}, {order.location_lng}\n"
    message += f"\n"
    
    message += f"🍽️ **ORDER DETAILS**\n"
    message += items_text
    message += f"💰 **Total: {order.total_amount} ETB**\n"
    message += f"💳 Payment: {order.payment_method.upper()}\n"
    if order.transaction_id:
        message += f"🆔 Transaction ID: {order.transaction_id}\n"
    message += f"\n"
    
    message += f"🚗 **DELIVERY INSTRUCTIONS**\n"
    message += f"1️⃣ Contact customer to confirm address\n"
    message += f"2️⃣ Pick up order from ET-FOOD Kitchen\n"
    message += f"3️⃣ Deliver to customer location\n"
    message += f"4️⃣ Collect payment if Cash on Delivery\n"
    message += f"5️⃣ Confirm delivery completion\n\n"
    
    message += f"🎯 **ACTION REQUIRED: Contact customer now!**"
    
    # Create action buttons
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": f"📞 Call Customer",
                    "url": f"tel:{order.customer_phone}"
                },
                {
                    "text": "💬 Message Customer",
                    "url": f"https://wa.me/{order.customer_phone.replace('+', '')}"
                }
            ],
            [
                {
                    "text": "📍 Open Maps",
                    "url": f"https://maps.google.com/?q={order.location_lat},{order.location_lng}" if order.location_lat else f"https://maps.google.com/?q={order.customer_address}"
                }
            ],
            [
                {
                    "text": "✅ Pickup Complete",
                    "callback_data": f"pickup_complete_{order.id}"
                },
                {
                    "text": "🚚 Delivery Complete",
                    "callback_data": f"delivery_complete_{order.id}"
                }
            ]
        ]
    }
    
    send_driver_message(driver_telegram_id, message, keyboard=keyboard)
    
    # Also send location if available
    if order.location_lat and order.location_lng:
        send_location_to_driver(driver_telegram_id, order.location_lat, order.location_lng, 
                              f"📍 Customer Location\n{order.customer_name}\n{order.customer_address}")

def send_location_to_driver(driver_telegram_id, lat, lng, title):
    """Send location to driver"""
    import requests
    import json
    
    url = f"https://api.telegram.org/bot{os.environ.get('DRIVER_BOT_TOKEN')}/sendLocation"
    
    data = {
        'chat_id': driver_telegram_id,
        'latitude': lat,
        'longitude': lng,
        'title': title
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print(f"Location sent to driver {driver_telegram_id}")
    except Exception as e:
        print(f"Error sending location: {e}")

def notify_customer_driver_assigned(order, driver):
    """Notify customer that driver has been assigned"""
    from bot_minimal import send_message
    
    message = f"🚗 *Driver Assigned to Your Order*\n\n"
    message += f"📋 Order #{order.id}\n"
    message += f"👨‍🚗 Driver: {driver.name}\n"
    message += f"📞 Driver Phone: {driver.phone_number}\n"
    message += f"🚗 Vehicle: {driver.vehicle_type}\n\n"
    message += f"⏰ Your order is being prepared and will be delivered soon!\n"
    message += f"📱 The driver will contact you for delivery coordination."
    
    send_message(order.telegram_user_id, message)

def test_complete_order_flow():
    """Test the complete order flow"""
    
    with app.app_context():
        # Get a test order
        order = Order.query.filter_by(status='confirmed').first()
        
        if not order:
            print("No confirmed orders found. Creating test order...")
            # Create test order
            order = Order(
                telegram_user_id=383870190,
                customer_name='Test Customer',
                customer_phone='+251944082812',
                customer_address='Bole, Addis Ababa, Ethiopia',
                items=[{
                    'id': 1,
                    'name': 'Beef Burger Normal',
                    'price': 400,
                    'quantity': 1,
                    'total': 400
                }],
                total_amount=400.0,
                payment_method='cash',
                status='confirmed',
                location_lat=9.150,
                location_lng=40.490
            )
            db.session.add(order)
            db.session.commit()
        
        print(f"Testing complete order flow with Order #{order.id}")
        
        # Find an available driver
        driver = Driver.query.filter_by(is_available=True, is_approved=True).first()
        
        if not driver:
            print("No available drivers found")
            return
            
        print(f"Assigning order to driver: {driver.name}")
        
        # Test driver acceptance
        success, message = handle_driver_order_acceptance(driver.telegram_user_id, order.id)
        
        if success:
            print(f"✅ {message}")
            print("Complete order information sent to driver")
        else:
            print(f"❌ {message}")

if __name__ == "__main__":
    test_complete_order_flow()