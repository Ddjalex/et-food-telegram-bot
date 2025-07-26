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
            from url_utils import construct_driver_panel_url
            driver_panel_url = construct_driver_panel_url(order.id, driver.id)
            
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
                # NOTE: Payment details (amount/method) are hidden from drivers per system requirements
                message = f"🚚 *New Delivery Assignment*\n\n"
                message += f"Order #{order.id}\n"
                message += f"Customer: {order.customer_name}\n"
                message += f"Phone: {order.customer_phone}\n"
                message += f"Address: {order.customer_address}\n\n"
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

def send_message_to_all_active_users(message):
    """Send message to all active users (customers who have used the bot recently)"""
    try:
        from models import Order, UserProfile
        from datetime import datetime, timedelta
        from app import app
        
        with app.app_context():
            # Get users who have placed orders in the last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_orders = Order.query.filter(Order.created_at >= thirty_days_ago).all()
            
            # Get unique user IDs from recent orders
            user_ids = set()
            for order in recent_orders:
                if order.telegram_user_id:
                    user_ids.add(order.telegram_user_id)
            
            # Also get users who have shared contact info (UserProfile)
            profiles = UserProfile.query.filter(UserProfile.created_at >= thirty_days_ago).all()
            for profile in profiles:
                if profile.telegram_user_id:
                    user_ids.add(profile.telegram_user_id)
            
            # Send message to all active users
            sent_count = 0
            for user_id in user_ids:
                try:
                    send_message(user_id, message, parse_mode="Markdown")
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
                    continue
            
            logger.info(f"Sent customer notification to {sent_count} active users")
            return sent_count
            
    except Exception as e:
        logger.error(f"Error sending message to all active users: {e}")
        return 0

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
            'confirmed': f'✅ Your order has been confirmed!\n\n💰 Please deposit {order.total_amount:.2f} ETB using one of these methods:\n\n🏦 **Commercial Bank of Ethiopia (CBE)**\nAccount: 1000123456789\nAccount Name: ET-FOOD Restaurant\n\n📱 **TeleBirr**\nPhone: +251-911-234567\nAccount Name: ET-FOOD\n\n🏪 **Dashen Bank**\nAccount: 0987654321012\nAccount Name: ET-FOOD Restaurant\n\n📞 **Contact us after deposit:**\n+251-911-123456\n\nAfter making the deposit, our admin will verify your payment and start preparing your order.',
            'payment_verified': '💳 Payment verified! Your order is now being prepared.',
            'preparing': '👨‍🍳 We are preparing your order.',
            'delivered': '🎉 Your order has been delivered!',
            'cancelled': '❌ Your order has been cancelled.'
        }

        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'payment_verified': '💳',
            'preparing': '👨‍🍳',
            'delivered': '🎉',
            'cancelled': '❌'
        }

        message = f"📦 *Order Update*\n\n"
        message += f"{status_messages.get(new_status, '')}\n\n"
        message += f"Status: {status_emoji.get(new_status)} {new_status.title()}\n"
        message += f"Total: {order.total_amount:.2f} ETB\n"
        message += f"Thank you for choosing ET-FOOD! 🍽️"

        # Add inline deposit buttons for confirmed orders
        keyboard = None
        if new_status == 'confirmed':
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🏦 CBE Bank", "callback_data": f"deposit_cbe_{order.id}"},
                        {"text": "📱 TeleBirr", "callback_data": f"deposit_telebirr_{order.id}"}
                    ],
                    [
                        {"text": "🏪 Dashen Bank", "callback_data": f"deposit_dashen_{order.id}"},
                        {"text": "📞 Contact Support", "callback_data": f"contact_support_{order.id}"}
                    ],
                    [
                        {"text": "💳 Payment Complete", "callback_data": f"payment_complete_{order.id}"}
                    ]
                ]
            }

        send_message(order.telegram_user_id, message, keyboard, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Failed to notify customer status change: {e}")

def notify_customer_order_rejected(order_id, reason):
    """Notify customer when kitchen rejects their order"""
    try:
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            logger.error(f"Order {order_id} not found for rejection notification")
            return

        message = f"❌ *Order Not Available*\n\n"
        message += f"🏪 Flavour Cafe | E.Fabrica cannot fulfill your order\n\n"
        message += f"📋 *Order #*{order.id}\n"
        message += f"⚠️ *Reason:* {reason}\n\n"
        message += f"We apologize for the inconvenience. Please try:\n"
        message += f"• Ordering different items from our menu\n"
        message += f"• Contacting us directly: +251-911-123456\n"
        message += f"• Trying again later\n\n"
        message += f"Thank you for understanding!"

        send_message(order.telegram_user_id, message, parse_mode='Markdown')
        logger.info(f"Rejection notification sent to customer {order.customer_name} for order #{order.id}")

    except Exception as e:
        logger.error(f"Failed to notify customer about order rejection: {e}")

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
    
    # Handle skip location
    if text == "⏭️ Skip Location":
        handle_skip_location(chat_id, user_id)
        return
    
    # Handle photo/image attachments (payment receipts)
    if 'photo' in message:
        handle_photo_attachment(chat_id, message['photo'], user_id, message.get('message_id'))
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
        # Check if user is admin before allowing access
        if is_admin_user(user_id):
            handle_admin_command(chat_id, text)
        else:
            send_message(chat_id, "❌ Access denied. This command is for administrators only.")
    elif text == "/orders":
        # Check if user is admin before allowing access
        if is_admin_user(user_id):
            handle_orders_command(chat_id, user_id)
        else:
            send_message(chat_id, "❌ Access denied. This command is for administrators only.")
    elif text == "/menuadmin":
        # Check if user is admin before allowing access
        if is_admin_user(user_id):
            handle_menu_admin_command(chat_id, user_id)
        else:
            send_message(chat_id, "❌ Access denied. This command is for administrators only.")
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
    if data.startswith(('confirm_order_', 'preparing_order_', 'assign_bot_', 'assign_driver_', 'delivered_order_', 'cancel_order_', 'select_driver_', 'accept_delivery_', 'decline_delivery_', 'verify_payment_', 'payment_not_found_')):
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
    elif data == "open_menu_again":
        # Handle "Order Again" button from delivery completion
        send_catalog(chat_id)
        send_message(chat_id, "🍽️ Welcome back! Choose from our delicious menu below.")
    elif data.startswith("rate_order_"):
        # Handle order rating
        parts = data.split("_")
        order_id = int(parts[2])
        rating = int(parts[3])
        handle_order_rating(order_id, rating, user_id)
        send_message(chat_id, f"⭐ Thank you for rating! Your {rating}-star rating has been recorded.")
        
        # Show order again option after rating
        keyboard = {
            "inline_keyboard": [
                [{
                    "text": "🍽️ Order Again",
                    "callback_data": "open_menu_again"
                }]
            ]
        }
        send_message(chat_id, "Would you like to place another order?", keyboard)
    elif data.startswith("feedback_"):
        # Handle feedback request
        order_id = data.split("_")[1]
        handle_feedback_request(chat_id, user_id, order_id)
    elif data.startswith("deposit_"):
        # Handle deposit button selections
        parts = data.split("_")
        deposit_method = parts[1]
        order_id = int(parts[2])
        
        # Get order details
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            send_message(chat_id, "❌ Order not found.")
            return
        
        # Create deposit instruction messages
        deposit_messages = {
            "cbe": f"🏦 **Commercial Bank of Ethiopia (CBE)**\n\n"
                   f"💰 Amount: {order.total_amount:.2f} ETB\n"
                   f"🔢 Account: 1000123456789\n"
                   f"👤 Account Name: ET-FOOD Restaurant\n\n"
                   f"📱 **Steps:**\n"
                   f"1. Open your mobile banking app\n"
                   f"2. Select 'Transfer Money'\n"
                   f"3. Enter the account number above\n"
                   f"4. Transfer {order.total_amount:.2f} ETB\n"
                   f"5. Take a screenshot of the receipt\n"
                   f"6. Click 'Payment Complete' below\n\n"
                   f"⏰ Please complete within 15 minutes",
            
            "telebirr": f"📱 **TeleBirr Payment**\n\n"
                        f"💰 Amount: {order.total_amount:.2f} ETB\n"
                        f"📞 Phone: +251-911-234567\n"
                        f"👤 Account Name: ET-FOOD\n\n"
                        f"📱 **Steps:**\n"
                        f"1. Open TeleBirr app\n"
                        f"2. Select 'Send Money'\n"
                        f"3. Enter phone number above\n"
                        f"4. Send {order.total_amount:.2f} ETB\n"
                        f"5. Take a screenshot of the receipt\n"
                        f"6. Click 'Payment Complete' below\n\n"
                        f"⏰ Please complete within 15 minutes",
            
            "dashen": f"🏪 **Dashen Bank**\n\n"
                      f"💰 Amount: {order.total_amount:.2f} ETB\n"
                      f"🔢 Account: 0987654321012\n"
                      f"👤 Account Name: ET-FOOD Restaurant\n\n"
                      f"📱 **Steps:**\n"
                      f"1. Open your Dashen mobile app\n"
                      f"2. Select 'Transfer'\n"
                      f"3. Enter the account number above\n"
                      f"4. Transfer {order.total_amount:.2f} ETB\n"
                      f"5. Take a screenshot of the receipt\n"
                      f"6. Click 'Payment Complete' below\n\n"
                      f"⏰ Please complete within 15 minutes",
            
            "support": f"📞 **Contact Support**\n\n"
                       f"💬 **WhatsApp:** +251-911-123456\n"
                       f"📞 **Phone:** +251-911-123456\n"
                       f"💰 **Your Order:** #{order.id}\n"
                       f"💵 **Amount:** {order.total_amount:.2f} ETB\n\n"
                       f"Our support team will help you with:\n"
                       f"• Payment assistance\n"
                       f"• Alternative payment methods\n"
                       f"• Order questions\n\n"
                       f"📱 Available 24/7"
        }
        
        message = deposit_messages.get(deposit_method, "Payment method not found")
        
        # Create back button and payment complete button
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🏦 CBE Bank", "callback_data": f"deposit_cbe_{order.id}"},
                    {"text": "📱 TeleBirr", "callback_data": f"deposit_telebirr_{order.id}"}
                ],
                [
                    {"text": "🏪 Dashen Bank", "callback_data": f"deposit_dashen_{order.id}"},
                    {"text": "📞 Contact Support", "callback_data": f"deposit_support_{order.id}"}
                ],
                [
                    {"text": "💳 Payment Complete", "callback_data": f"payment_complete_{order.id}"}
                ]
            ]
        }
        
        send_message(chat_id, message, keyboard, parse_mode='Markdown')
    
    elif data.startswith("payment_complete_"):
        # Handle payment completion notification - REQUIRE SCREENSHOT
        order_id = int(data.split("_")[2])
        
        # Get order details
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            send_message(chat_id, "❌ Order not found.")
            return
        
        # Check if payment screenshot was uploaded
        if not order.transaction_image_url:
            send_message(chat_id, "❌ **Payment Screenshot Required**\n\n📸 Please upload a screenshot of your payment receipt first, then click 'Payment Complete'.\n\n**How to upload:**\n1. Take a screenshot of your payment receipt\n2. Send the image to this chat\n3. Then click 'Payment Complete' button", parse_mode='Markdown')
            return
        
        # Update order status to payment_pending (waiting for admin verification)
        from extensions import db
        order.status = 'payment_pending'
        db.session.commit()
        
        # Notify customer
        confirmation_message = f"✅ **Payment Confirmation Received**\n\n"
        confirmation_message += f"📦 Order #{order.id}\n"
        confirmation_message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
        confirmation_message += f"🔍 Our admin team will verify your payment shortly.\n"
        confirmation_message += f"⏰ This usually takes 2-5 minutes.\n\n"
        confirmation_message += f"📱 You'll receive a notification once verified.\n"
        confirmation_message += f"Thank you for your patience! 😊"
        
        send_message(chat_id, confirmation_message, parse_mode='Markdown')
        
        # Notify admin about payment completion
        try:
            from models import AdminUser
            admins = AdminUser.query.filter_by(is_active=True).all()
            
            admin_message = f"💳 **Payment Completion Reported**\n\n"
            admin_message += f"📦 Order #{order.id}\n"
            admin_message += f"👤 Customer: {order.customer_name}\n"
            admin_message += f"📞 Phone: {order.customer_phone}\n"
            admin_message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
            admin_message += f"🔍 **Please verify the payment and update order status**"
            
            admin_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Payment Verified", "callback_data": f"verify_payment_{order.id}"},
                        {"text": "❌ Payment Not Found", "callback_data": f"payment_not_found_{order.id}"}
                    ]
                ]
            }
            
            for admin in admins:
                send_message(admin.telegram_user_id, admin_message, admin_keyboard, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to notify admin about payment completion: {e}")
    
    elif data.startswith("verify_payment_"):
        # Handle admin payment verification
        order_id = int(data.split("_")[2])
        
        # Check if user is admin
        from models import AdminUser
        admin = AdminUser.query.filter_by(telegram_user_id=user_id).first()
        if not admin:
            return
        
        # Update order status
        from models import Order
        from extensions import db
        order = Order.query.get(order_id)
        if order:
            order.status = 'payment_verified'
            db.session.commit()
            
            # Notify customer
            notify_customer_status_change(order_id, 'payment_verified')
            
            # Update admin message
            url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
            requests.post(url, json={
                "chat_id": chat_id,
                "message_id": callback_query["message"]["message_id"],
                "text": f"✅ Payment verified for Order #{order_id}",
                "parse_mode": "Markdown"
            })
    
    elif data.startswith("payment_not_found_"):
        # Handle payment not found
        order_id = int(data.split("_")[3])
        
        # Check if user is admin
        from models import AdminUser
        admin = AdminUser.query.filter_by(telegram_user_id=user_id).first()
        if not admin:
            return
        
        # Get order details
        from models import Order
        order = Order.query.get(order_id)
        if not order:
            return
        
        # Notify customer about payment issue
        issue_message = f"❌ **Payment Verification Issue**\n\n"
        issue_message += f"📦 Order #{order.id}\n"
        issue_message += f"💰 Amount: {order.total_amount:.2f} ETB\n\n"
        issue_message += f"🔍 We couldn't find your payment in our system.\n"
        issue_message += f"📱 Please contact support or try again:\n"
        issue_message += f"📞 +251-911-123456\n\n"
        issue_message += f"💡 **Tips:**\n"
        issue_message += f"• Check if transfer was successful\n"
        issue_message += f"• Verify account numbers\n"
        issue_message += f"• Contact your bank if needed"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🔄 Try Payment Again", "callback_data": f"deposit_cbe_{order.id}"},
                    {"text": "📞 Contact Support", "callback_data": f"deposit_support_{order.id}"}
                ]
            ]
        }
        
        send_message(order.telegram_user_id, issue_message, keyboard, parse_mode='Markdown')
        
        # Update admin message
        url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/editMessageText"
        requests.post(url, json={
            "chat_id": chat_id,
            "message_id": callback_query["message"]["message_id"],
            "text": f"❌ Payment not found for Order #{order_id} - Customer notified",
            "parse_mode": "Markdown"
        })
    
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
                        vehicle_type="automated"
                    )
                    delivery_bot.is_active = True
                    delivery_bot.is_available = True
                    delivery_bot.is_approved = True
                    delivery_bot.approval_status = "approved"
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
        from app import app
        
        with app.app_context():
            user_profile = UserProfile.query.filter_by(telegram_user_id=user_id).first()
            if not user_profile:
                user_profile = UserProfile()
                user_profile.telegram_user_id = user_id
                db.session.add(user_profile)
            
            user_profile.phone_number = phone_number
            user_profile.first_name = first_name
            db.session.commit()
            
        # Send success message
        send_message(chat_id, f"✅ Phone number saved: {phone_number}")
        
        # Request location sharing for nearby restaurant detection
        location_keyboard = {
            "keyboard": [
                [{
                    "text": "📍 Share My Location",
                    "request_location": True
                }],
                [{
                    "text": "⏭️ Skip Location"
                }]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        send_message(chat_id, 
                    "📍 Please share your location to find nearby restaurants and get better delivery estimates.\n\n"
                    "This helps us:\n"
                    "• Find restaurants closest to you\n"
                    "• Calculate accurate delivery times\n"
                    "• Show distance-based recommendations\n\n"
                    "You can share your location or skip this step:", 
                    location_keyboard)
        
    except Exception as e:
        logger.error(f"Failed to save contact: {e}")
        send_message(chat_id, "❌ Failed to save contact. Please try again.")

def handle_location_share(chat_id, location, user_id):
    """Handle location sharing and find nearby restaurants"""
    lat = location.get('latitude')
    lng = location.get('longitude')
    
    try:
        from models import UserProfile, db, Restaurant
        from app import app
        
        with app.app_context():
            user_profile = UserProfile.query.filter_by(telegram_user_id=user_id).first()
            if not user_profile:
                user_profile = UserProfile()
                user_profile.telegram_user_id = user_id
                db.session.add(user_profile)
            
            user_profile.location_lat = lat
            user_profile.location_lng = lng
            db.session.commit()
            
            # Find nearby restaurants
            restaurants = Restaurant.query.filter_by(is_active=True).all()
            nearby_restaurants = []
            
            for restaurant in restaurants:
                if restaurant.latitude and restaurant.longitude:
                    # Calculate distance using Haversine formula
                    from math import radians, cos, sin, asin, sqrt
                    
                    lat1, lon1 = radians(lat), radians(lng)
                    lat2, lon2 = radians(restaurant.latitude), radians(restaurant.longitude)
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    distance = 6371 * c  # Earth's radius in kilometers
                    
                    if distance <= 10:  # Within 10km
                        nearby_restaurants.append({
                            'name': restaurant.name,
                            'distance': round(distance, 2),
                            'address': restaurant.address
                        })
            
            # Sort by distance
            nearby_restaurants.sort(key=lambda x: x['distance'])
            
            # Simple location confirmation without restaurant list
            location_msg = f"✅ Location saved successfully!\n📍 GPS: {lat:.4f}, {lng:.4f}"
            send_message(chat_id, location_msg)
        
        # Show modern delivery app WebApp after location
        from config import Config
        webapp_url = f"{Config.WEBHOOK_URL}/webapp"
        
        keyboard = {
            "inline_keyboard": [[{
                "text": "🍽️ Open Menu",
                "web_app": {"url": webapp_url}
            }]]
        }
        send_message(chat_id, "🍽️ Ready to order! Your location will help us show nearby restaurants first.", keyboard)
        
    except Exception as e:
        logger.error(f"Failed to save location: {e}")
        send_message(chat_id, "❌ Failed to save location. Please try again.")

def handle_skip_location(chat_id, user_id):
    """Handle when user skips location sharing"""
    try:
        # Show modern delivery app WebApp without location
        from config import Config
        webapp_url = f"{Config.WEBHOOK_URL}/webapp"
        
        keyboard = {
            "inline_keyboard": [[{
                "text": "🍽️ Open Menu",
                "web_app": {"url": webapp_url}
            }]]
        }
        
        send_message(chat_id, 
                    "⏭️ Location sharing skipped.\n\n"
                    "You can still browse all restaurants, but:\n"
                    "• Restaurant distance won't be shown\n"
                    "• Delivery time estimates may be less accurate\n"
                    "• You'll see all restaurants instead of nearby ones\n\n"
                    "🍽️ Ready to order!", 
                    keyboard)
        
    except Exception as e:
        logger.error(f"Failed to handle skip location: {e}")
        send_message(chat_id, "❌ Something went wrong. Please try again.")

def handle_photo_attachment(chat_id, photo, user_id, message_id=None):
    """Handle photo/image attachments (payment receipts)"""
    try:
        # Get the largest photo size
        photo_info = photo[-1]  # Last item is usually the largest
        file_id = photo_info['file_id']
        
        # Send acknowledgment message
        receipt_message = f"📸 **Payment Receipt Received**\n\n"
        receipt_message += f"✅ Thank you for uploading your payment receipt!\n\n"
        receipt_message += f"🔍 **Next Steps:**\n"
        receipt_message += f"• Our admin team will verify your payment\n"
        receipt_message += f"• You'll receive confirmation within 2-5 minutes\n"
        receipt_message += f"• Once verified, your order will be processed\n\n"
        receipt_message += f"📱 We'll notify you as soon as payment is confirmed.\n"
        receipt_message += f"Thank you for your patience! 😊"
        
        send_message(chat_id, receipt_message, parse_mode='Markdown')
        
        # Find the user's most recent order that's awaiting payment
        from models import Order, AdminUser
        from app import app, db
        
        with app.app_context():
            recent_order = Order.query.filter_by(
                telegram_user_id=user_id,
                status='confirmed'
            ).order_by(Order.created_at.desc()).first()
            
            if not recent_order:
                # If no confirmed order found, check for any recent order
                recent_order = Order.query.filter_by(
                    telegram_user_id=user_id
                ).order_by(Order.created_at.desc()).first()
            
            if recent_order:
                # Get file path from Telegram and store screenshot URL in database
                try:
                    file_info_url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getFile"
                    file_response = requests.get(file_info_url, params={'file_id': file_id})
                    file_data = file_response.json()
                    
                    if file_data.get('ok'):
                        file_path = file_data['result']['file_path']
                        file_url = f"https://api.telegram.org/file/bot{Config.BOT_TOKEN}/{file_path}"
                        recent_order.transaction_image_url = file_url
                        db.session.commit()
                    else:
                        logger.error(f"Failed to get file info: {file_data}")
                except Exception as e:
                    logger.error(f"Failed to get file URL: {e}")
                    # Store file_id as fallback
                    recent_order.transaction_image_url = f"telegram_file_id:{file_id}"
                    db.session.commit()
                
                # Notify admin about receipt upload
                admins = AdminUser.query.filter_by(is_active=True).all()
                logger.info(f"Found {len(admins)} admin users for notification")
                
                if admins:
                    admin_message = f"📸 **Payment Receipt Uploaded**\n\n"
                    admin_message += f"📦 Order #{recent_order.id}\n"
                    admin_message += f"👤 Customer: {recent_order.customer_name}\n"
                    admin_message += f"📞 Phone: {recent_order.customer_phone}\n"
                    admin_message += f"💰 Amount: {recent_order.total_amount:.2f} ETB\n"
                    admin_message += f"📅 Order Date: {recent_order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                    admin_message += f"🔍 **Please verify the payment receipt and update order status**"
                    
                    admin_keyboard = {
                        "inline_keyboard": [
                            [
                                {"text": "✅ Payment Verified", "callback_data": f"verify_payment_{recent_order.id}"},
                                {"text": "❌ Payment Not Found", "callback_data": f"payment_not_found_{recent_order.id}"}
                            ],
                            [
                                {"text": "📱 View Receipt", "callback_data": f"view_receipt_{file_id}"}
                            ]
                        ]
                    }
                    
                    # Send notifications to all admins
                    for admin in admins:
                        try:
                            logger.info(f"Notifying admin {admin.telegram_user_id} about payment receipt")
                            
                            # Forward the photo if we have message_id
                            if message_id:
                                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/forwardMessage"
                                response = requests.post(url, json={
                                    "chat_id": admin.telegram_user_id,
                                    "from_chat_id": chat_id,
                                    "message_id": message_id
                                })
                                logger.info(f"Photo forward response: {response.status_code} - {response.text}")
                            else:
                                # Send the photo directly using sendPhoto
                                url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendPhoto"
                                response = requests.post(url, json={
                                    "chat_id": admin.telegram_user_id,
                                    "photo": file_id,
                                    "caption": f"Payment receipt from {recent_order.customer_name} (Order #{recent_order.id})"
                                })
                                logger.info(f"Photo send response: {response.status_code} - {response.text}")
                            
                            # Send admin message with verification buttons
                            send_message(admin.telegram_user_id, admin_message, admin_keyboard, parse_mode='Markdown')
                            logger.info(f"Successfully notified admin {admin.telegram_user_id}")
                            
                        except Exception as e:
                            logger.error(f"Failed to notify admin {admin.telegram_user_id}: {e}")
                else:
                    logger.warning("No active admin users found for payment receipt notification")
                        
            else:
                # No recent order found
                support_message = f"📸 **Receipt Received**\n\n"
                support_message += f"We received your payment receipt, but couldn't find a recent order.\n\n"
                support_message += f"📞 Please contact support:\n"
                support_message += f"WhatsApp: +251-911-123456\n"
                support_message += f"Phone: +251-911-123456\n\n"
                support_message += f"Include your order number and payment details."
                
                send_message(chat_id, support_message, parse_mode='Markdown')
                
    except Exception as e:
        logger.error(f"Failed to handle photo attachment: {e}")
        send_message(chat_id, "❌ Failed to process receipt. Please try again or contact support.")

def is_admin_user(user_id):
    """Check if a user is an admin"""
    try:
        from models import AdminUser
        from app import app
        
        with app.app_context():
            admin = AdminUser.query.filter_by(telegram_user_id=user_id, is_active=True).first()
            return admin is not None
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id}: {e}")
        return False

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
        from app import app
        
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

def handle_order_rating(order_id, rating, user_id):
    """Handle order rating submission"""
    try:
        from extensions import db
        from models import Order
        
        order = Order.query.get(order_id)
        if order and order.telegram_user_id == user_id:
            # Store rating in order (you might want to add a rating field to Order model)
            # For now, we'll log it and notify admin
            logger.info(f"Order #{order_id} rated {rating} stars by user {user_id}")
            
            # Notify admin about the rating
            admin_message = f"⭐ **Customer Rating Received**\n\n"
            admin_message += f"📋 Order #{order_id}\n"
            admin_message += f"⭐ Rating: {rating} stars\n"
            admin_message += f"👤 Customer: {order.customer_name}\n"
            admin_message += f"💰 Amount: {order.total_amount:.2f} ETB"
            
            # Send to all active admins
            from models import AdminUser, Driver
            admins = AdminUser.query.filter_by(is_active=True).all()
            for admin in admins:
                if admin.telegram_user_id:
                    send_message_to_admin(admin.telegram_user_id, admin_message)
            
            # Notify the driver about the rating
            driver = Driver.query.filter_by(id=order.driver_id).first()
            if driver and driver.telegram_user_id:
                from driver_bot import send_driver_message
                
                # Create star display
                stars = "⭐" * rating
                driver_rating_message = f"🎉 **Customer Rating Received!**\n\n"
                driver_rating_message += f"📋 Order #{order_id}\n"
                driver_rating_message += f"⭐ Rating: {stars} ({rating}/5)\n"
                driver_rating_message += f"👤 Customer: {order.customer_name}\n"
                driver_rating_message += f"💰 Order value: {order.total_amount:.2f} ETB\n\n"
                driver_rating_message += f"🎯 Great job! Keep up the excellent service!\n"
                driver_rating_message += f"📊 This rating helps improve your driver profile."
                
                # Add buttons for driver actions
                rating_keyboard = {
                    "inline_keyboard": [
                        [
                            {
                                "text": "📊 View All Ratings",
                                "callback_data": "driver_earnings"
                            },
                            {
                                "text": "🔄 Check Status",
                                "callback_data": "driver_status"
                            }
                        ]
                    ]
                }
                
                send_driver_message(driver.telegram_user_id, driver_rating_message, keyboard=rating_keyboard)
                    
    except Exception as e:
        logger.error(f"Error handling order rating: {e}")

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
        from app import app
        
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