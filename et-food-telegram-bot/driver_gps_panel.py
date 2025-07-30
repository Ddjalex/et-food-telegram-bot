"""
Driver GPS Panel System
Inline GPS navigation interface for drivers directly in Telegram chat
"""

from driver_bot import send_driver_message, logger, calculate_distance

def send_driver_gps_panel(chat_id, order_id):
    """Send comprehensive Driver Panel with GPS navigation directly in chat"""
    try:
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            send_driver_message(chat_id, "❌ Order not found.")
            return
        
        # Calculate distance to customer
        restaurant_lat, restaurant_lng = 9.047658, 38.741143
        customer_lat, customer_lng = order.location_lat or 9.025000, order.location_lng or 38.750000
        distance = calculate_distance((restaurant_lat, restaurant_lng), (customer_lat, customer_lng))
        
        # GPS Navigation Panel Message
        message = f"""🗺️ *DRIVER PANEL - GPS NAVIGATION*

📋 *Order #{order.id}*
🚗 *Status: OUT FOR DELIVERY*

👤 *Customer Information:*
▫️ Name: {order.customer_name}
▫️ Phone: {order.customer_phone}
▫️ Address: {order.customer_address}
▫️ Payment: {order.payment_method}
▫️ Amount: {order.total_amount:.2f} ETB

🎯 *GPS Coordinates:*
▫️ Customer Location: {customer_lat}, {customer_lng}
▫️ Distance to Customer: {distance:.1f} km

🏪 *Restaurant Information:*
▫️ ET-FOOD Kitchen
▫️ Location: 9.047658, 38.741143
▫️ Phone: +251911234567

📍 *Live Location Status:*
▫️ GPS Tracking: ACTIVE
▫️ Real-time Updates: Every 30 seconds
▫️ Customer Notifications: ENABLED

🧭 *Navigation Instructions:*
▫️ Current Step: Navigate to customer
▫️ Next Action: Call customer upon arrival
▫️ ETA: {int(distance * 3)} minutes (approx)

⚠️ *Important Notes:*
▫️ Keep GPS location sharing ON
▫️ Contact customer before arrival
▫️ Confirm delivery completion

🔄 *Use buttons below for quick actions:*"""
        
        # GPS Navigation Keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📞 Call Customer",
                        "callback_data": f"call_customer_{order_id}"
                    },
                    {
                        "text": "📞 Call Restaurant", 
                        "callback_data": "call_restaurant"
                    }
                ],
                [
                    {
                        "text": "🗺️ Navigate to Customer",
                        "callback_data": f"navigate_customer_{order_id}"
                    },
                    {
                        "text": "🏪 Navigate to Restaurant",
                        "callback_data": "navigate_restaurant"
                    }
                ],
                [
                    {
                        "text": "📍 Share Live Location",
                        "callback_data": f"share_location_{order_id}"
                    },
                    {
                        "text": "🔄 Refresh GPS",
                        "callback_data": f"driver_panel_{order_id}"
                    }
                ],
                [
                    {
                        "text": "✅ Pickup Complete",
                        "callback_data": f"pickup_complete_{order_id}"
                    },
                    {
                        "text": "✅ Delivery Complete",
                        "callback_data": f"delivery_complete_{order_id}"
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error sending driver GPS panel: {e}")
        send_driver_message(chat_id, "❌ Error loading GPS navigation panel")

def handle_navigate_to_customer(chat_id, order_id):
    """Handle navigation to customer location"""
    try:
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            send_driver_message(chat_id, "❌ Order not found.")
            return
        
        customer_lat = order.location_lat or 9.025000
        customer_lng = order.location_lng or 38.750000
        
        message = f"""🗺️ *NAVIGATION TO CUSTOMER*

📍 *Destination:*
▫️ {order.customer_name}
▫️ {order.customer_address}
▫️ GPS: {customer_lat}, {customer_lng}

🚗 *Navigation Options:*
▫️ Tap Google Maps to open turn-by-turn navigation
▫️ Tap Waze for alternative route
▫️ Use GPS coordinates for manual navigation

📞 *Contact Information:*
▫️ Customer: {order.customer_phone}
▫️ Restaurant: +251911234567

⚠️ *Before Arrival:*
▫️ Call customer 5 minutes before arrival
▫️ Confirm delivery address
▫️ Prepare payment receipt if needed"""
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🗺️ Open Google Maps",
                        "url": f"https://www.google.com/maps/dir/?api=1&destination={customer_lat},{customer_lng}&travelmode=driving"
                    },
                    {
                        "text": "🚗 Open Waze",
                        "url": f"https://waze.com/ul?ll={customer_lat},{customer_lng}&navigate=yes"
                    }
                ],
                [
                    {
                        "text": "📞 Call Customer",
                        "callback_data": f"call_customer_{order_id}"
                    },
                    {
                        "text": "📍 Share Location",
                        "callback_data": f"share_location_{order_id}"
                    }
                ],
                [
                    {
                        "text": "⬅️ Back to Driver Panel",
                        "callback_data": f"driver_panel_{order_id}"
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling navigation to customer: {e}")
        send_driver_message(chat_id, "❌ Error loading navigation")

def handle_navigate_to_restaurant(chat_id):
    """Handle navigation to restaurant"""
    restaurant_lat, restaurant_lng = 9.047658, 38.741143
    
    message = f"""🏪 *NAVIGATION TO RESTAURANT*

📍 *Destination:*
▫️ ET-FOOD Kitchen
▫️ Addis Ababa, Ethiopia
▫️ GPS: {restaurant_lat}, {restaurant_lng}

🚗 *Navigation Options:*
▫️ Tap Google Maps for turn-by-turn navigation
▫️ Tap Waze for alternative route
▫️ Use GPS coordinates for manual navigation

📞 *Restaurant Contact:*
▫️ Phone: +251911234567
▫️ Call to confirm order pickup

⚠️ *Pickup Instructions:*
▫️ Show order number upon arrival
▫️ Verify order items before leaving
▫️ Confirm pickup completion in app"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🗺️ Open Google Maps",
                    "url": f"https://www.google.com/maps/dir/?api=1&destination={restaurant_lat},{restaurant_lng}&travelmode=driving"
                },
                {
                    "text": "🚗 Open Waze",
                    "url": f"https://waze.com/ul?ll={restaurant_lat},{restaurant_lng}&navigate=yes"
                }
            ],
            [
                {
                    "text": "📞 Call Restaurant",
                    "callback_data": "call_restaurant"
                },
                {
                    "text": "📍 Share Location",
                    "callback_data": "share_location"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard, parse_mode="Markdown")

def handle_call_customer(chat_id, order_id):
    """Handle calling customer with order details"""
    try:
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            send_driver_message(chat_id, "❌ Order not found.")
            return
        
        message = f"""📞 *CUSTOMER CONTACT*

👤 *Customer Information:*
▫️ Name: {order.customer_name}
▫️ Phone: {order.customer_phone}
▫️ Address: {order.customer_address}
▫️ Order: #{order.id}

💬 *Call Script Suggestions:*
▫️ "Hello, this is your ET-FOOD delivery driver"
▫️ "I'm on my way with your order #{order.id}"
▫️ "I'll be there in approximately X minutes"
▫️ "Please confirm your address: {order.customer_address}"

⚠️ *Important Notes:*
▫️ Be polite and professional
▫️ Confirm delivery address
▫️ Mention any delivery issues
▫️ Estimate arrival time accurately"""
        
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📞 Call Now",
                        "url": f"tel:{order.customer_phone.replace('+', '')}"
                    }
                ],
                [
                    {
                        "text": "⬅️ Back to Driver Panel",
                        "callback_data": f"driver_panel_{order_id}"
                    }
                ]
            ]
        }
        
        send_driver_message(chat_id, message, keyboard=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error handling call customer: {e}")
        send_driver_message(chat_id, "❌ Error loading customer contact")

def handle_call_restaurant(chat_id):
    """Handle calling restaurant"""
    message = f"""📞 *RESTAURANT CONTACT*

🏪 *ET-FOOD Kitchen*
▫️ Phone: +251911234567
▫️ Address: Addis Ababa, Ethiopia

💬 *Call Script Suggestions:*
▫️ "Hello, this is an ET-FOOD delivery driver"
▫️ "I'm here to pick up order #[ORDER_NUMBER]"
▫️ "Is the order ready for pickup?"
▫️ "How long will it take to prepare?"

⚠️ *Important Notes:*
▫️ Show order number upon arrival
▫️ Verify order items before leaving
▫️ Report any delays to customer
▫️ Confirm pickup completion in app"""
    
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📞 Call Restaurant",
                    "url": "tel:+251911234567"
                }
            ]
        ]
    }
    
    send_driver_message(chat_id, message, keyboard=keyboard, parse_mode="Markdown")