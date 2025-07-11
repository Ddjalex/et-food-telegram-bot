import logging
import requests
from flask import request, jsonify
from config import Config

logger = logging.getLogger(__name__)

def send_message(chat_id, text, keyboard=None, parse_mode=None):
    """Send a message to Telegram"""
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        data["reply_markup"] = keyboard
    if parse_mode:
        data["parse_mode"] = parse_mode

    response = requests.post(url, json=data)
    result = response.json()
    if not result.get("ok"):
        # Handle "chat not found" errors gracefully
        if result.get('error_code') == 400 and 'chat not found' in result.get('description', '').lower():
            logger.warning(f"Chat {chat_id} not found - user has not started the bot yet")
        else:
            logger.error(f"Failed to send message: {result}")

def notify_driver_assignment(driver_id, order_id):
    """Notify driver about order assignment"""
    try:
        from models import Driver, Order
        driver = Driver.query.get(driver_id)
        order = Order.query.get(order_id)
        
        if not driver or not order:
            return
            
        # If it's a bot driver, send automated response and integrate with driver panel
        if driver.name == "Delivery Bot":
            # Send automated location updates for bot driver
            send_bot_location_updates(driver_id, order_id)
            
            # Send notification to admin about bot assignment
            admin_message = f"🤖 *Delivery Bot Assignment*\n\n"
            admin_message += f"Order #{order.id} assigned to Delivery Bot\n"
            admin_message += f"Customer: {order.customer_name}\n"
            admin_message += f"Phone: {order.customer_phone}\n"
            admin_message += f"Address: {order.customer_address}\n"
            admin_message += f"Total: {order.total_amount:.2f} ETB\n\n"
            admin_message += f"🚚 Delivery Bot is now processing your order..."
            
            # Create driver panel URL for monitoring
            import os
            # Construct clean URL for driver panel
            render_url = os.environ.get('RENDER_EXTERNAL_URL')
            replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
            
            if render_url:
                base_url = render_url.replace('https://', '').replace('http://', '')
            elif replit_domain:
                base_url = replit_domain.replace('https://', '').replace('http://', '')
            else:
                base_url = 'localhost'
            
            driver_panel_url = f"https://{base_url}/driver-panel?order_id={order.id}&driver_id={driver.id}"
            
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "📱 Monitor Bot Panel",
                            "web_app": {"url": driver_panel_url}
                        }
                    ],
                    [
                        {
                            "text": "📍 Track Location",
                            "callback_data": f"track_bot_{order.id}"
                        },
                        {
                            "text": "🎯 Override Manual",
                            "callback_data": f"override_bot_{order.id}"
                        }
                    ]
                ]
            }
            
            # Send simple customer notification (without admin details)
            customer_message = f"🚚 *Your order is being prepared for delivery!*\n\n"
            customer_message += f"💰 Total: {order.total_amount:.2f} ETB\n"
            customer_message += f"📍 Our delivery team will contact you soon with tracking information.\n\n"
            customer_message += f"Thank you for choosing ET-FOOD! 🍽️"
            
            send_message(order.telegram_user_id, customer_message, parse_mode="Markdown")
            
            # Send to admins with monitoring options
            try:
                send_order_notification(order.id)
            except Exception as e:
                logger.error(f"Error sending admin notification: {e}")
            
            # Auto-accept the order for bot driver
            from extensions import db
            order.status = 'out_for_delivery'
            db.session.commit()
            
        elif driver.telegram_user_id:
            # Try to use driver bot first, fallback to main bot
            try:
                from driver_bot import notify_driver_assignment_via_driver_bot
                order_data = order.to_dict()
                logger.info(f"Attempting to notify driver {driver.name} (Telegram ID: {driver.telegram_user_id}) about order {order.id}")
                notify_driver_assignment_via_driver_bot(driver.telegram_user_id, order_data)
            except Exception as driver_bot_error:
                logger.warning(f"Driver bot notification failed, using main bot: {driver_bot_error}")
                
                # This is driver notification - should NOT go to customer
                # Send to driver only (this is fallback for driver bot failure)
                message = f"🚚 *New Delivery Assignment*\n\n"
                message += f"Order #{order.id}\n"
                message += f"Customer: {order.customer_name}\n"
                message += f"Phone: {order.customer_phone}\n"
                message += f"Address: {order.customer_address}\n"
                message += f"Total: {order.total_amount:.2f} ETB\n\n"
                message += f"📍 Please share your live location to help admin track delivery progress."
                
                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ Accept & Share Location", "callback_data": f"accept_delivery_{order.id}"},
                            {"text": "❌ Decline", "callback_data": f"decline_delivery_{order.id}"}
                        ],
                        [
                            {"text": "📍 Share Live Location", "callback_data": f"share_location_{driver.id}"}
                        ]
                    ]
                }
                
                send_message(driver.telegram_user_id, message, keyboard=keyboard, parse_mode="Markdown")
        else:
            logger.warning(f"Driver {driver.name} (ID: {driver.id}) has no telegram_user_id set. Cannot send notification.")
            
    except Exception as e:
        logger.error(f"Error notifying driver: {e}")

def send_bot_location_updates(driver_id, order_id):
    """Send simulated location updates for delivery bot"""
    import threading
    import time
    from datetime import datetime
    
    def simulate_delivery():
        try:
            # Get Flask app context for database operations
            from app import app
            
            with app.app_context():
                from extensions import db
                from models import Driver, Order
                
                # Simulate delivery route with location updates
                locations = [
                    (9.145, 40.489658),  # Restaurant location (Addis Ababa)
                    (9.150, 40.495),     # En route 1
                    (9.155, 40.500),     # En route 2
                    (9.160, 40.505),     # En route 3
                    (9.165, 40.510),     # Customer location
                ]
                
                for i, (lat, lng) in enumerate(locations):
                    time.sleep(30)  # 30 seconds between updates
                    
                    driver = Driver.query.get(driver_id)
                    if not driver:
                        break
                        
                    driver.current_lat = lat
                    driver.current_lng = lng
                    driver.last_location_update = datetime.utcnow()
                    db.session.commit()
                    
                    # Notify admin of location update
                    notify_admin_location_update(driver_id, order_id, lat, lng, i + 1, len(locations))
                    
                    # If final location, mark as delivered
                    if i == len(locations) - 1:
                        time.sleep(60)  # Wait 1 minute at delivery location
                        order = Order.query.get(order_id)
                        if order:
                            order.status = 'delivered'
                            driver.is_available = True
                            db.session.commit()
                            notify_customer_status_change(order_id, 'delivered')
                        
        except Exception as e:
            logger.error(f"Error in bot location simulation: {e}")
    
    # Start simulation in background thread
    thread = threading.Thread(target=simulate_delivery)
    thread.daemon = True
    thread.start()

def notify_admin_location_update(driver_id, order_id, lat, lng, step, total_steps):
    """Notify admin about driver location update"""
    try:
        from models import AdminUser
        admins = AdminUser.query.filter_by(is_active=True).all()
        
        progress = (step / total_steps) * 100
        status_emoji = "🚚" if step < total_steps else "📍"
        
        message = f"{status_emoji} *Driver Location Update*\n\n"
        message += f"Order #{order_id}\n"
        message += f"Driver: Delivery Bot\n"
        message += f"Progress: {progress:.0f}%\n"
        message += f"Location: {lat:.6f}, {lng:.6f}\n"
        
        if step == total_steps:
            message += f"\n✅ Arrived at customer location!"
        
        for admin in admins:
            send_message(admin.telegram_user_id, message, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error notifying admin location update: {e}")

def request_driver_location(driver_id):
    """Request live location from driver"""
    try:
        from models import Driver
        driver = Driver.query.get(driver_id)
        
        if not driver or not driver.telegram_user_id:
            return
            
        message = "📍 Please share your current location to help admin track deliveries."
        
        keyboard = {
            "keyboard": [[{
                "text": "📍 Share Live Location",
                "request_location": True
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        send_message(driver.telegram_user_id, message, keyboard=keyboard)
        
    except Exception as e:
        logger.error(f"Error requesting driver location: {e}")

# Driver location handling moved to driver_bot.py

def send_message_to_admin(admin_telegram_id, message):
    """Send message to specific admin"""
    try:
        send_message(admin_telegram_id, message, parse_mode="Markdown")
        logger.info(f"Message sent to admin {admin_telegram_id}")
    except Exception as e:
        # Handle "chat not found" gracefully
        if "chat not found" in str(e).lower():
            logger.warning(f"Admin {admin_telegram_id} has not started the bot yet - message not sent")
        else:
            logger.error(f"Error sending message to admin {admin_telegram_id}: {e}")

def send_order_notification(order_id):
    """Send order notification to admins"""
    try:
        from models import Order, AdminUser
        order = Order.query.get(order_id)
        admins = AdminUser.query.filter_by(is_active=True).all()

        if not order or not admins:
            return

        message = f"🆕 *New Order #{order.id}*\n\n"
        message += f"Customer: {order.customer_name}\n"
        message += f"Phone: {order.customer_phone}\n"
        message += f"Address: {order.customer_address}\n"
        message += f"Total: {order.total_amount:.2f} ETB\n"
        message += f"Payment: {order.payment_method}\n\n"

        admin_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Confirm", "callback_data": f"confirm_order_{order.id}"},
                    {"text": "👨‍🍳 Preparing", "callback_data": f"preparing_order_{order.id}"}
                ],
                [
                    {"text": "🚚 Assign Bot", "callback_data": f"assign_bot_{order.id}"},
                    {"text": "👤 Assign Driver", "callback_data": f"assign_driver_{order.id}"}
                ],
                [
                    {"text": "🚚 Delivered", "callback_data": f"delivered_order_{order.id}"},
                    {"text": "❌ Cancel", "callback_data": f"cancel_order_{order.id}"}
                ]
            ]
        }

        for admin in admins:
            send_message(admin.telegram_user_id, message, admin_keyboard, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Failed to send order notification: {e}")

def notify_customer_status_change(order_id, new_status):
    """Notify customer when order status changes"""
    try:
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            return

        status_messages = {
            'confirmed': '✅ Your order has been confirmed!',
            'preparing': '👨‍🍳 We are preparing your order.',
            'delivered': '🎉 Your order has been delivered!',
            'cancelled': '❌ Your order has been cancelled.'
        }

        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'preparing': '👨‍🍳',
            'delivered': '🎉',
            'cancelled': '❌'
        }

        message = f"📦 *Order Update*\n\n"
        message += f"{status_messages.get(new_status, '')}\n\n"
        message += f"Status: {status_emoji.get(new_status)} {new_status.title()}\n"
        message += f"Total: {order.total_amount:.2f} ETB\n"
        message += f"Thank you for choosing ET-FOOD! 🍽️"

        send_message(order.telegram_user_id, message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Failed to notify customer status change: {e}")

def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]

    # Handle contact sharing
    if 'contact' in message:
        handle_contact_share(chat_id, message['contact'], user_id)
        return
    
    # Handle location sharing
    if 'location' in message:
        handle_location_share(chat_id, message['location'], user_id)
        return

    if text == "/start":
        send_start_message(chat_id)
    elif text == "/menu":
        if check_user_registration(chat_id, user_id):
            send_menu_message(chat_id)
        else:
            send_start_message(chat_id)
    elif text == "/track":
        if check_user_registration(chat_id, user_id):
            send_track_message(chat_id, user_id)
        else:
            send_start_message(chat_id)
    elif text == "/admin":
        handle_admin_command(chat_id, text)
    elif text == "/orders":
        handle_orders_command(chat_id, user_id)
    elif text == "/menuadmin":
        handle_menu_admin_command(chat_id, user_id)
    elif text == "/contact":
        send_contact_request(chat_id)
    # Handle keyboard button presses
    elif text == "🛒 Catalog":
        if check_user_registration(chat_id, user_id):
            send_catalog(chat_id)
        else:
            send_start_message(chat_id)
    elif text == "🛍️ My cart":
        if check_user_registration(chat_id, user_id):
            send_cart_info(chat_id, user_id)
        else:
            send_start_message(chat_id)
    elif text == "⚙️ Settings":
        if check_user_registration(chat_id, user_id):
            send_settings_menu(chat_id)
        else:
            send_start_message(chat_id)
    elif text == "📝 Leave a review":
        if check_user_registration(chat_id, user_id):
            send_review_form(chat_id)
        else:
            send_start_message(chat_id)
    elif text == "🏔️ Go to main":
        if check_user_registration(chat_id, user_id):
            send_main_menu(chat_id)
        else:
            send_start_message(chat_id)
    elif text == "🍔 Burgers":
        if check_user_registration(chat_id, user_id):
            send_category_products(chat_id, "burgers")
        else:
            send_start_message(chat_id)
    elif text == "🍟 Snacks":
        if check_user_registration(chat_id, user_id):
            send_category_products(chat_id, "snacks")
        else:
            send_start_message(chat_id)
    elif text == "🥫 Sauces":
        if check_user_registration(chat_id, user_id):
            send_category_products(chat_id, "sauces")
        else:
            send_start_message(chat_id)
    elif text == "🥤 Drinks":
        if check_user_registration(chat_id, user_id):
            send_category_products(chat_id, "drinks")
        else:
            send_start_message(chat_id)
    else:
        send_message(chat_id, "🤖 I didn't understand that. Try /start or /menu.")
        # Check if user is in feedback mode
        if check_feedback_mode(user_id):
            handle_feedback_submission(chat_id, user_id, text)
        else:
            send_message(chat_id, "🤖 I didn't understand that. Try /start or /menu.")

def handle_callback_query(callback_query):
    chat_id = callback_query["message"]["chat"]["id"]
    data = callback_query["data"]
    user_id = callback_query["from"]["id"]
    
    # Admin callback handlers
    if data.startswith(('confirm_order_', 'preparing_order_', 'assign_bot_', 'assign_driver_', 'delivered_order_', 'cancel_order_', 'select_driver_', 'accept_delivery_', 'decline_delivery_')):
        handle_admin_callback(callback_query)
        return
    
    if data == "share_contact":
        keyboard = {
            "keyboard": [[{
                "text": "📱 Send phone number",
                "request_contact": True
            }]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        send_message(chat_id, "Please, send or type your phone number", keyboard)
    elif data == "main_menu":
        send_main_menu(chat_id)
    elif data.startswith("category_"):
        category = data.replace("category_", "")
        send_category_products(chat_id, category)
    elif data == "catalog":
        send_catalog(chat_id)
    elif data == "leave_feedback":
        handle_feedback_request(chat_id, user_id)
    elif data == "cancel_feedback":
        feedback_mode_users.discard(user_id)
        send_message(chat_id, "❌ Feedback cancelled.")
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "🍽️ Open Menu",
                    "web_app": {"url": f"{Config.WEBHOOK_URL}/webapp"}
                }],
                [{"text": "💬 Leave Feedback", "callback_data": "leave_feedback"}]
            ]
        }
        send_message(chat_id, "What would you like to do?", keyboard)
    elif data == "settings":
        send_settings_menu(chat_id)
    elif data == "cart":
        send_cart_info(chat_id, user_id)
    elif data == "review":
        send_review_form(chat_id)
    else:
        send_message(chat_id, f"📦 You selected: {data}")

def handle_admin_callback(callback_query):
    """Handle admin callback queries"""
    try:
        from extensions import db
        from models import Order, Driver, AdminUser
        
        chat_id = callback_query["message"]["chat"]["id"]
        data = callback_query["data"]
        message_id = callback_query["message"]["message_id"]
        user_id = callback_query["from"]["id"]
        
        # Check if user is admin
        admin = AdminUser.query.filter_by(telegram_user_id=user_id).first()
        if not admin:
            return
        
        if data.startswith('confirm_order_'):
            order_id = int(data.split('_')[2])
            order = Order.query.get(order_id)
            if order:
                order.status = 'confirmed'
                db.session.commit()
                notify_customer_status_change(order_id, 'confirmed')
                
                # Update the message
                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
                requests.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ Order #{order_id} has been confirmed",
                    "parse_mode": "Markdown"
                })
        
        elif data.startswith('preparing_order_'):
            order_id = int(data.split('_')[2])
            order = Order.query.get(order_id)
            if order:
                order.status = 'preparing'
                db.session.commit()
                notify_customer_status_change(order_id, 'preparing')
                
                # Update the message
                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
                requests.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"👨‍🍳 Order #{order_id} is being prepared",
                    "parse_mode": "Markdown"
                })
        
        elif data.startswith('assign_bot_'):
            order_id = int(data.split('_')[2])
            order = Order.query.get(order_id)
            if order:
                # Find or create delivery bot
                delivery_bot = Driver.query.filter_by(name="Delivery Bot").first()
                if not delivery_bot:
                    delivery_bot = Driver(
                        name="Delivery Bot",
                        phone_number="+251900000000",
                        vehicle_type="automated",
                        is_active=True,
                        is_available=True,
                        is_approved=True,
                        approval_status="approved"
                    )
                    db.session.add(delivery_bot)
                    db.session.commit()
                
                # Assign bot to order
                order.driver_id = delivery_bot.id
                order.status = 'out_for_delivery'
                db.session.commit()
                
                # Notify customer
                notify_customer_status_change(order_id, 'out_for_delivery')
                
                # Update admin message
                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
                requests.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"🤖 Order #{order_id} assigned to Delivery Bot",
                    "parse_mode": "Markdown"
                })
        
        elif data.startswith('assign_driver_'):
            order_id = int(data.split('_')[2])
            # Show available drivers for assignment
            drivers = Driver.query.filter_by(is_available=True, is_approved=True).all()
            human_drivers = [d for d in drivers if d.name != "Delivery Bot"]
            if human_drivers:
                driver_keyboard = {
                    "inline_keyboard": []
                }
                for driver in human_drivers[:5]:  # Limit to 5 drivers
                    driver_keyboard["inline_keyboard"].append([
                        {"text": f"👤 {driver.name}", "callback_data": f"select_driver_{driver.id}_{order_id}"}
                    ])
                
                send_message(chat_id, f"Select a driver for Order #{order_id}:", keyboard=driver_keyboard)
            else:
                send_message(chat_id, "❌ No available drivers found")
        
        elif data.startswith('select_driver_'):
            parts = data.split('_')
            driver_id = int(parts[2])
            order_id = int(parts[3])
            
            driver = Driver.query.get(driver_id)
            order = Order.query.get(order_id)
            
            if driver and order:
                order.driver_id = driver_id
                order.status = 'out_for_delivery'
                driver.is_available = False
                db.session.commit()
                
                # Notify driver and customer
                notify_driver_assignment(driver_id, order_id)
                notify_customer_status_change(order_id, 'out_for_delivery')
                
                send_message(chat_id, f"✅ Order #{order_id} assigned to {driver.name}")
        
        elif data.startswith('delivered_order_'):
            order_id = int(data.split('_')[2])
            order = Order.query.get(order_id)
            if order:
                order.status = 'delivered'
                if order.driver_id:
                    driver = Driver.query.get(order.driver_id)
                    if driver and driver.name != "Delivery Bot":
                        driver.is_available = True
                db.session.commit()
                notify_customer_status_change(order_id, 'delivered')
                
                # Update the message
                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
                requests.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"🚚 Order #{order_id} has been delivered",
                    "parse_mode": "Markdown"
                })
        
        elif data.startswith('cancel_order_'):
            order_id = int(data.split('_')[2])
            order = Order.query.get(order_id)
            if order:
                if order.driver_id:
                    driver = Driver.query.get(order.driver_id)
                    if driver and driver.name != "Delivery Bot":
                        driver.is_available = True
                order.status = 'cancelled'
                db.session.commit()
                notify_customer_status_change(order_id, 'cancelled')
                
                # Update the message
                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
                requests.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"❌ Order #{order_id} has been cancelled",
                    "parse_mode": "Markdown"
                })
        
        elif data.startswith('accept_delivery_'):
            order_id = int(data.split('_')[2])
            order = Order.query.get(order_id)
            if order:
                order.status = 'out_for_delivery'
                db.session.commit()
                notify_customer_status_change(order_id, 'out_for_delivery')
                
                # Request live location from driver
                from models import Driver
                driver = Driver.query.filter_by(telegram_user_id=user_id).first()
                if driver:
                    request_driver_location(driver.id)
                
                # Update driver message
                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
                requests.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ You accepted delivery for Order #{order_id}\n\n📍 Please share your live location to help admin track the delivery.",
                    "parse_mode": "Markdown"
                })
        
        elif data.startswith('share_location_'):
            driver_id = int(data.split('_')[2])
            request_driver_location(driver_id)
        
        elif data.startswith('decline_delivery_'):
            order_id = int(data.split('_')[2])
            order = Order.query.get(order_id)
            if order:
                # Make driver available again
                if order.driver_id:
                    driver = Driver.query.get(order.driver_id)
                    if driver:
                        driver.is_available = True
                order.driver_id = None
                order.status = 'confirmed'
                db.session.commit()
                
                # Update driver message
                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
                requests.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"❌ You declined delivery for Order #{order_id}",
                    "parse_mode": "Markdown"
                })
                
    except Exception as e:
        logger.error(f"Error handling admin callback query: {e}")

def init_bot(flask_app):
    """Initialize the Telegram bot with Flask app context"""
    if not Config.BOT_TOKEN or Config.BOT_TOKEN == 'your_bot_token_here':
        logger.warning("BOT_TOKEN not configured - bot functionality disabled")
        return

    logger.info("Initializing Telegram bot...")

    if not any(rule.endpoint == 'webhook' for rule in flask_app.url_map.iter_rules()):
        @flask_app.route('/webhook', methods=['POST'], endpoint='webhook')
        def webhook():
            try:
                update = request.get_json()
                logger.info(f"Webhook received: {update}")

                if update and 'message' in update:
                    logger.info(f"Processing message: {update['message']}")
                    handle_message(update['message'])
                elif update and 'callback_query' in update:
                    logger.info(f"Processing callback query: {update['callback_query']}")
                    handle_callback_query(update['callback_query'])

                return jsonify({'status': 'ok'})
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        logger.info("Webhook endpoint created")
    else:
        logger.warning("Webhook route already exists. Skipping registration.")

    set_webhook_once()

def send_start_message(chat_id):
    """Send welcome message with mandatory contact sharing"""
    keyboard = {
        "keyboard": [[{
            "text": "📱 Send phone number",
            "request_contact": True
        }]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    send_message(chat_id, "Welcome to our bot! 🍽️\n\nPlease, send or type your phone number", keyboard)

def send_menu_message(chat_id):
    """Send menu with WebApp button"""
    keyboard = {
        "inline_keyboard": [[{
            "text": "🍽️ Open Menu",
            "web_app": {"url": f"{Config.WEBHOOK_URL}/webapp"}
        }]]
    }
    send_message(chat_id, "📋 Browse our delicious menu:", keyboard)

def send_main_menu(chat_id):
    """Send main menu with category buttons"""
    keyboard = {
        "keyboard": [
            [{"text": "🛒 Catalog"}, {"text": "🛍️ My cart"}],
            [{"text": "⚙️ Settings"}, {"text": "📝 Leave a review"}],
            [{"text": "🏔️ Go to main"}]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "Choose an option:", keyboard)

def send_catalog(chat_id):
    """Send catalog with WebApp"""
    keyboard = {
        "inline_keyboard": [[{
            "text": "🛒 Open Catalog",
            "web_app": {"url": f"{Config.WEBHOOK_URL}/webapp"}
        }]]
    }
    send_message(chat_id, "🛒 Browse our catalog:", keyboard)

def send_category_products(chat_id, category):
    """Send category-specific products"""
    keyboard = {
        "inline_keyboard": [[{
            "text": f"View {category.title()}",
            "web_app": {"url": f"{Config.WEBHOOK_URL}/webapp?category={category}"}
        }]]
    }
    send_message(chat_id, f"🍽️ {category.title()} menu:", keyboard)

def send_settings_menu(chat_id):
    """Send settings menu"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🌐 Language", "callback_data": "language"}],
            [{"text": "📍 Location", "callback_data": "location"}],
            [{"text": "🔔 Notifications", "callback_data": "notifications"}],
            [{"text": "◀️ Back", "callback_data": "main_menu"}]
        ]
    }
    send_message(chat_id, "⚙️ Settings:", keyboard)

def send_cart_info(chat_id, user_id):
    """Send cart information"""
    keyboard = {
        "inline_keyboard": [[{
            "text": "🛒 View Cart",
            "web_app": {"url": f"{Config.WEBHOOK_URL}/webapp#cart"}
        }]]
    }
    send_message(chat_id, "🛒 Your cart:", keyboard)

def send_review_form(chat_id):
    """Send review form"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "⭐⭐⭐⭐⭐", "callback_data": "review_5"}],
            [{"text": "⭐⭐⭐⭐", "callback_data": "review_4"}],
            [{"text": "⭐⭐⭐", "callback_data": "review_3"}],
            [{"text": "◀️ Back", "callback_data": "main_menu"}]
        ]
    }
    send_message(chat_id, "📝 Rate our service:", keyboard)

def send_track_message(chat_id, user_id):
    """Send order tracking information"""
    keyboard = {
        "inline_keyboard": [[{
            "text": "📋 View Orders",
            "web_app": {"url": f"{Config.WEBHOOK_URL}/webapp#orders"}
        }]]
    }
    send_message(chat_id, "📦 Track your orders:", keyboard)

def handle_contact_share(chat_id, contact, user_id):
    """Handle contact sharing and request location"""
    phone_number = contact.get('phone_number', '')
    first_name = contact.get('first_name', '')
    
    # Save to database
    try:
        from models import UserProfile, db
        from main import app
        
        with app.app_context():
            user_profile = UserProfile.query.filter_by(telegram_user_id=user_id).first()
            if not user_profile:
                user_profile = UserProfile(telegram_user_id=user_id)
                db.session.add(user_profile)
            
            user_profile.phone_number = phone_number
            user_profile.first_name = first_name
            db.session.commit()
            
        # Send success message and go directly to menu
        send_message(chat_id, f"✅ Phone number saved: {phone_number}")
        
        # Show menu WebApp directly
        from config import Config
        webapp_url = f"{Config.WEBHOOK_URL}/webapp"
        
        keyboard = {
            "inline_keyboard": [[{
                "text": "🍽️ Open Menu",
                "web_app": {"url": webapp_url}
            }]]
        }
        send_message(chat_id, "🍽️ Welcome! Ready to order some delicious food?", keyboard)
        
    except Exception as e:
        logger.error(f"Failed to save contact: {e}")
        send_message(chat_id, "❌ Failed to save contact. Please try again.")

def handle_location_share(chat_id, location, user_id):
    """Handle location sharing (optional - save for delivery)"""
    lat = location.get('latitude')
    lng = location.get('longitude')
    
    try:
        from models import UserProfile, db
        from main import app
        
        with app.app_context():
            user_profile = UserProfile.query.filter_by(telegram_user_id=user_id).first()
            if not user_profile:
                user_profile = UserProfile(telegram_user_id=user_id)
                db.session.add(user_profile)
            
            user_profile.location_lat = lat
            user_profile.location_lng = lng
            db.session.commit()
            
        send_message(chat_id, f"📍 Location saved for delivery!")
        
        # Show menu WebApp after location (if user shares location later)
        from config import Config
        webapp_url = f"{Config.WEBHOOK_URL}/webapp"
        
        keyboard = {
            "inline_keyboard": [[{
                "text": "🍽️ Open Menu",
                "web_app": {"url": webapp_url}
            }]]
        }
        send_message(chat_id, "🍽️ Ready to order!", keyboard)
        
    except Exception as e:
        logger.error(f"Failed to save location: {e}")
        send_message(chat_id, "❌ Failed to save location. Please try again.")

def handle_admin_command(chat_id, text):
    """Handle admin commands"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Dashboard", "url": f"{Config.WEBHOOK_URL}/admin"}],
            [{"text": "📋 Orders", "callback_data": "admin_orders"}],
            [{"text": "🍽️ Menu", "callback_data": "admin_menu"}]
        ]
    }
    send_message(chat_id, "🔐 Admin Panel:", keyboard)

def handle_orders_command(chat_id, user_id):
    """Handle orders command for admins"""
    keyboard = {
        "inline_keyboard": [[{
            "text": "📊 View Dashboard",
            "url": f"{Config.WEBHOOK_URL}/admin"
        }]]
    }
    send_message(chat_id, "📋 Admin Orders Dashboard:", keyboard)

def handle_menu_admin_command(chat_id, user_id):
    """Handle menu admin command"""
    keyboard = {
        "inline_keyboard": [[{
            "text": "🍽️ Menu Management",
            "url": f"{Config.WEBHOOK_URL}/admin#menu"
        }]]
    }
    send_message(chat_id, "🍽️ Menu Management:", keyboard)

def send_contact_request(chat_id):
    """Send contact sharing request"""
    keyboard = {
        "keyboard": [[{
            "text": "📱 Send phone number",
            "request_contact": True
        }]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    send_message(chat_id, "Please share your contact information:", keyboard)

def check_user_registration(chat_id, user_id):
    """Check if user has shared both contact and location"""
    try:
        from models import UserProfile, db
        from main import app
        
        with app.app_context():
            user_profile = UserProfile.query.filter_by(telegram_user_id=user_id).first()
            if not user_profile:
                return False
            
            # Check if both phone number and location are provided
            has_contact = user_profile.phone_number is not None and user_profile.phone_number != ""
            has_location = user_profile.location_lat is not None and user_profile.location_lng is not None
            
            if not has_contact:
                send_message(chat_id, "❌ Please share your phone number first using /start")
                return False
            elif not has_location:
                send_message(chat_id, "❌ Please share your location first")
                keyboard = {
                    "keyboard": [[{
                        "text": "📍 Share live location",
                        "request_location": True
                    }]],
                    "resize_keyboard": True,
                    "one_time_keyboard": True
                }
                send_message(chat_id, "Please share your live location for delivery:", keyboard)
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to check user registration: {e}")
        return False

# Global variable to track users in feedback mode
feedback_mode_users = set()

def check_feedback_mode(user_id):
    """Check if user is in feedback mode"""
    return user_id in feedback_mode_users

def handle_feedback_request(chat_id, user_id):
    """Handle feedback request from user"""
    # Add user to feedback mode
    feedback_mode_users.add(user_id)
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "❌ Cancel", "callback_data": "cancel_feedback"}]
        ]
    }
    
    send_message(chat_id, "💬 Please type your feedback message:\n\n(Your message will be sent to our admin team)", keyboard)

def handle_feedback_submission(chat_id, user_id, feedback_text):
    """Handle feedback submission and send to admins"""
    # Remove user from feedback mode
    feedback_mode_users.discard(user_id)
    
    try:
        # Get user info
        from models import UserProfile, AdminUser
        from main import app
        
        with app.app_context():
            user_profile = UserProfile.query.filter_by(telegram_user_id=user_id).first()
            admins = AdminUser.query.filter_by(is_active=True).all()
            
            user_name = "Unknown User"
            user_phone = "Not provided"
            
            if user_profile:
                user_name = f"{user_profile.first_name or ''} {user_profile.last_name or ''}".strip()
                user_phone = user_profile.phone_number or "Not provided"
            
            # Send feedback to admins
            admin_message = f"📝 *New Customer Feedback*\n\n"
            admin_message += f"👤 From: {user_name}\n"
            admin_message += f"📱 Phone: {user_phone}\n"
            admin_message += f"🆔 User ID: {user_id}\n\n"
            admin_message += f"💬 Message:\n{feedback_text}"
            
            # Send to all admins
            for admin in admins:
                send_message(admin.telegram_user_id, admin_message, parse_mode='Markdown')
            
            # Also send to a default admin if no admins found
            if not admins:
                # You can set a default admin chat ID here
                default_admin_id = 383870190  # This should be replaced with actual admin ID
                send_message(default_admin_id, admin_message, parse_mode='Markdown')
        
        # Confirm to user
        send_message(chat_id, "✅ Thank you for your feedback! Your message has been sent to our team.")
        
        # Show main options again
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "🍽️ Open Menu",
                    "web_app": {"url": f"{Config.WEBHOOK_URL}/webapp"}
                }],
                [{"text": "💬 Leave Another Feedback", "callback_data": "leave_feedback"}]
            ]
        }
        send_message(chat_id, "What would you like to do next?", keyboard)
        
    except Exception as e:
        logger.error(f"Failed to send feedback: {e}")
        send_message(chat_id, "❌ Sorry, there was an error sending your feedback. Please try again later.")

def set_webhook_once():
    """Set webhook only if it is not already set correctly"""
    try:
        expected_url = f"{Config.WEBHOOK_URL}/webhook"
        get_url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getWebhookInfo"
        current_info = requests.get(get_url).json()

        current_url = current_info.get("result", {}).get("url", "")
        if current_url != expected_url:
            logger.info(f"Updating webhook to: {expected_url}")
            set_url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/setWebhook"
            response = requests.post(set_url, data={"url": expected_url})
            result = response.json()
            if result.get('ok'):
                logger.info(f"Webhook set successfully: {expected_url}")
            else:
                logger.error(f"Failed to set webhook: {result}")
        else:
            logger.info("Webhook already set correctly. No update needed.")

    except Exception as e:
        logger.error(f"Error setting webhook: {e}")