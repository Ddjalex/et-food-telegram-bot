"""
Payment Workflow System for ET-FOOD
Handles deposit requirements, payment verification, and order preparation workflow
"""

from flask import Blueprint, request, jsonify, render_template
from models import db, Order, MenuItem, Restaurant, KitchenStaff
from datetime import datetime
import os

payment_workflow = Blueprint('payment_workflow', __name__)

def notify_kitchen_staff_payment_verified(order):
    """Notify kitchen staff that payment has been verified"""
    try:
        from real_time_notifications import send_telegram_notification
        
        # Get kitchen staff for this restaurant
        kitchen_staff = KitchenStaff.query.filter_by(
            restaurant_id=order.restaurant_id,
            is_active=True
        ).all()
        
        message = f"💳 *PAYMENT VERIFIED*\n\n"
        message += f"🆔 **Order**: #{order.id}\n"
        message += f"👤 **Customer**: {order.customer_name}\n"
        message += f"💰 **Amount**: {order.total_amount:.2f} ETB\n"
        message += f"✅ **Status**: Payment Confirmed\n\n"
        message += f"🍳 **Action Required**: Start preparing the order"
        
        for staff in kitchen_staff:
            if staff.telegram_user_id:
                send_telegram_notification(staff.telegram_user_id, message)
        
        return True
    except Exception as e:
        logger.error(f"Error notifying kitchen staff: {e}")
        return False

def notify_customer_payment_approved(order):
    """Notify customer that payment has been approved"""
    try:
        from real_time_notifications import send_telegram_notification
        
        if not hasattr(order, 'telegram_user_id') or not order.telegram_user_id:
            return False
        
        message = f"✅ *PAYMENT APPROVED*\n\n"
        message += f"🆔 **Order**: #{order.id}\n"
        message += f"💰 **Amount**: {order.total_amount:.2f} ETB\n"
        message += f"✅ **Status**: Payment Verified\n\n"
        message += f"🍳 **Next Step**: Your order is now being prepared!\n"
        message += f"⏰ **Estimated Time**: 15-30 minutes"
        
        send_telegram_notification(order.telegram_user_id, message)
        return True
    except Exception as e:
        logger.error(f"Error notifying customer: {e}")
        return False

@payment_workflow.route('/api/kitchen/food-available', methods=['POST'])
def kitchen_food_available():
    """Kitchen staff marks food as available - triggers deposit requirement"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
            
        # Calculate deposit amount (50% of total)
        deposit_amount = order.total_amount * 0.5
        
        # Update order status to require deposit
        order.status = 'deposit_required'
        order.deposit_amount = deposit_amount
        order.deposit_deadline = datetime.utcnow().replace(hour=23, minute=59, second=59)  # End of day
        
        db.session.commit()
        
        # Send notification to customer about deposit requirement
        send_deposit_notification(order)
        
        return jsonify({
            'success': True,
            'message': 'Food marked as available. Customer deposit required.',
            'deposit_amount': deposit_amount,
            'order_id': order_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payment_workflow.route('/api/customer/submit-deposit', methods=['POST'])
def submit_deposit():
    """Customer submits deposit payment with proof"""
    try:
        order_id = request.form.get('order_id')
        payment_method = request.form.get('payment_method')
        transaction_id = request.form.get('transaction_id')
        
        order = Order.query.get(order_id)
        if not order or order.status != 'deposit_required':
            return jsonify({'error': 'Invalid order or deposit not required'}), 400
            
        # Handle payment screenshot upload
        payment_screenshot = None
        if 'payment_screenshot' in request.files:
            file = request.files['payment_screenshot']
            if file and file.filename:
                filename = f"deposit_{order_id}_{datetime.now().timestamp()}_{file.filename}"
                filepath = os.path.join('static/uploads', filename)
                file.save(filepath)
                payment_screenshot = f"/static/uploads/{filename}"
        
        # Update order with payment information
        order.payment_method = payment_method
        order.transaction_id = transaction_id
        order.transaction_image_url = payment_screenshot
        order.status = 'pending'  # Set to pending for admin verification
        
        db.session.commit()
        
        # Send real-time notification for payment verification
        try:
            from real_time_notifications import notify_payment_verification_needed
            notify_payment_verification_needed(order.id)
        except Exception as e:
            logger.error(f"Error sending payment notification: {e}")
        
        return jsonify({
            'success': True,
            'message': 'Payment information submitted successfully. Awaiting admin verification.',
            'order_id': order.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payment_workflow.route('/api/admin/verify-payment', methods=['POST'])
def verify_payment():
    """Restaurant admin verifies customer deposit payment"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        admin_decision = data.get('decision')  # 'approve' or 'reject'
        admin_notes = data.get('notes', '')
        
        # For simplified workflow, directly work with order_id instead of transaction_id
        order_id = data.get('order_id', transaction_id)
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        if admin_decision == 'approve':
            # Update order status to confirmed
            order.status = 'confirmed'
            order.payment_verified_at = datetime.utcnow()
            
            # Send real-time notifications
            try:
                from real_time_notifications import notify_order_status_change
                notify_order_status_change(order.id, 'confirmed', admin_action=True)
            except Exception as e:
                print(f"Notification error: {e}")
            
            message = 'Payment verified successfully. Order confirmed.'
            
        else:
            # Reject payment
            order.status = 'cancelled'
            order.cancellation_reason = admin_notes or "Payment verification failed"
            
            message = 'Payment rejected. Order cancelled.'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'order_status': order.status
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payment_workflow.route('/api/kitchen/start-preparation', methods=['POST'])
def start_preparation():
    """Kitchen starts preparing order - triggers driver search"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        order = Order.query.get(order_id)
        if not order or order.status != 'payment_verified':
            return jsonify({'error': 'Order not ready for preparation'}), 400
            
        # Update order status
        order.status = 'preparing'
        order.preparation_started_at = datetime.utcnow()
        
        db.session.commit()
        
        # Search for nearby drivers
        nearby_drivers = search_nearby_drivers(order)
        
        # Notify customer that preparation started
        notify_customer_preparation_started(order)
        
        return jsonify({
            'success': True,
            'message': 'Order preparation started. Searching for drivers.',
            'nearby_drivers': len(nearby_drivers),
            'order_status': 'preparing'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Notification functions
def send_deposit_notification(order):
    """Send deposit requirement notification to customer"""
    from bot_minimal import send_message_to_user
    
    message = f"""
🏪 *Flavour Cafe | E.Fabrica*

✅ Your order is available for preparation!

💰 *Deposit Required*
Amount: {order.deposit_amount:.2f} ETB
Deadline: Today 11:59 PM

📋 *Order Details:*
Order #{order.id}
Total: {order.total_amount:.2f} ETB

Please submit your deposit payment to proceed with order preparation.

💳 *Payment Methods:*
• CBE Birr: 1000-xxxx-xxxx
• M-Pesa: +251-911-123456  
• Bank Transfer: CBE Account 10001234567890

After payment, upload screenshot via the app.
    """
    
    if order.telegram_user_id:
        send_message_to_user(order.telegram_user_id, message)

def notify_admin_payment_verification(order, transaction):
    """Notify restaurant admin about payment verification needed"""
    from bot_minimal import send_message_to_all_active_users
    
    message = f"""
🏪 *Payment Verification Required*

📋 *Order #* {order.id}
👤 *Customer:* {order.customer_name}
💰 *Deposit:* {transaction.amount:.2f} ETB
💳 *Method:* {transaction.payment_method}
🆔 *Transaction:* {transaction.transaction_id}

⏰ Submitted: {transaction.created_at.strftime('%H:%M')}

Please verify payment in admin dashboard.
    """
    
    # Send to restaurant admins only
    send_message_to_all_active_users(message, user_type='admin')

def notify_kitchen_start_preparation(order):
    """Notify kitchen staff through web dashboard - NOT Telegram"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Log notification for kitchen web dashboard to pick up
        logger.info(f"🚨 KITCHEN ALERT: Order #{order.id} payment verified - Ready for preparation!")
        logger.info(f"Customer: {order.customer_name}, Total: {order.total_amount:.2f} ETB")
        logger.info(f"Kitchen staff should check web dashboard at /kitchen/orders")
        
        # Kitchen staff will see this order in the web dashboard at /kitchen/orders
        # No Telegram notifications needed - they use the web interface
        
        logger.info(f"Kitchen staff notified for Order #{order.id}")
        
    except Exception as e:
        logger.error(f"Error notifying kitchen staff: {e}")

def notify_customer_payment_approved(order):
    """Notify customer that payment was approved"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from bot_minimal import send_message
        
        message = f"""
✅ *Payment Verified!*

💰 Your deposit has been confirmed
👨‍🍳 Kitchen will start preparing your order

📋 *Order #* {order.id}
🏪 Flavour Cafe | E.Fabrica

⏱️ Estimated preparation: 15-25 minutes
🚚 We'll find a driver once ready

Track your order in the app!
        """
        
        if order.telegram_user_id:
            send_message(order.telegram_user_id, message, parse_mode='Markdown')
            logger.info(f"Payment approval notification sent to customer {order.customer_name}")
        else:
            logger.warning(f"No Telegram user ID for order {order.id} customer {order.customer_name}")
            
    except Exception as e:
        logger.error(f"Error notifying customer of payment approval: {e}")

def notify_customer_payment_rejected(order, reason):
    """Notify customer that payment was rejected"""
    from bot_minimal import send_message_to_user
    
    message = f"""
❌ *Payment Verification Failed*

📋 Order #{order.id}
⚠️ Reason: {reason}

Please resubmit your deposit with:
• Clear payment screenshot
• Correct transaction ID
• Valid payment method

Contact restaurant: +251-911-123456
    """
    
    if order.telegram_user_id:
        send_message_to_user(order.telegram_user_id, message)

def notify_customer_preparation_started(order):
    """Notify customer that preparation started"""
    from bot_minimal import send_message_to_user
    
    message = f"""
👨‍🍳 *Cooking Started!*

🍽️ Your order is being prepared
📋 Order #{order.id}

⏱️ Estimated time: 15-25 minutes
🚚 We're searching for nearby drivers

You'll be notified when ready for delivery!
    """
    
    if order.telegram_user_id:
        send_message_to_user(order.telegram_user_id, message)

def search_nearby_drivers(order):
    """Search for nearby available drivers for specific restaurant"""
    from enhanced_driver_system import find_nearby_drivers, notify_drivers_about_order
    
    # Get restaurant coordinates for this specific order
    restaurant = Restaurant.query.get(order.restaurant_id)
    if not restaurant or not restaurant.latitude or not restaurant.longitude:
        # Fallback coordinates for Flavour Cafe if no coordinates in database
        restaurant_lat = 9.047658
        restaurant_lng = 38.741143
    else:
        restaurant_lat = restaurant.latitude
        restaurant_lng = restaurant.longitude
    
    # Find drivers within 10km radius for this restaurant only
    nearby_drivers = find_nearby_drivers(
        restaurant_lat=restaurant_lat,
        restaurant_lng=restaurant_lng,
        radius_km=10,
        restaurant_id=order.restaurant_id  # Pass restaurant filter
    )
    
    if nearby_drivers:
        # Notify drivers about the order
        notify_drivers_about_order(order.id, nearby_drivers)
    
    return nearby_drivers

def notify_kitchen_realtime(order):
    """Send real-time notification to kitchen web dashboard"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Kitchen staff use web dashboard at /kitchen/orders - no Telegram needed
        logger.info(f"🚨 KITCHEN ALERT: Order #{order.id} payment verified - Ready for preparation!")
        logger.info(f"Customer: {order.customer_name}, Total: {order.total_amount:.2f} ETB")
        logger.info(f"Kitchen staff should start preparing Order #{order.id} immediately")
        
        # Kitchen dashboard will show this order with 'confirmed' status
        # Staff can see all new confirmed orders in their web interface
        
    except Exception as e:
        logger.error(f"Error sending kitchen real-time notification: {e}")

def notify_kitchen_staff_payment_verified(order):
    """Send real-time notification to kitchen staff when payment is verified"""
    try:
        # Get kitchen staff for this restaurant
        kitchen_staff = KitchenStaff.query.filter_by(
            restaurant_id=order.restaurant_id,
            is_active=True
        ).all()
        
        if not kitchen_staff:
            print(f"No active kitchen staff found for restaurant {order.restaurant_id}")
            return
        
        # Send notifications to kitchen staff via Telegram
        from bot_minimal import send_message_to_user
        
        for staff in kitchen_staff:
            if staff.telegram_user_id:
                try:
                    message = f"""
🔔 **PAYMENT VERIFIED - NEW ORDER**

📋 **Order #{order.id}**
👤 Customer: {order.customer_name}
💰 Amount: {order.total_amount} ETB
💳 Payment Method: {order.payment_method or 'N/A'}
📍 Address: {order.customer_address or 'N/A'}

✅ Payment has been verified by admin
🍽️ **Please start preparing the order**

Order Status: CONFIRMED → PREPARING
                    """
                    
                    send_message_to_user(staff.telegram_user_id, message)
                    print(f"Kitchen staff notification sent to {staff.name} (ID: {staff.telegram_user_id})")
                    
                except Exception as e:
                    print(f"Error sending notification to kitchen staff {staff.name}: {e}")
                    
    except Exception as e:
        print(f"Error in notify_kitchen_staff_payment_verified: {e}")