"""
Food Availability System
Handles notifying customers when ordered food is available or unavailable
"""

from app import app, db
from models import Order, MenuItem, AdminUser
from bot_minimal import send_message, notify_customer_status_change
import json

def check_food_availability(order_id):
    """
    Check if all items in an order are available
    Returns: (available, unavailable_items)
    """
    with app.app_context():
        order = Order.query.get(order_id)
        if not order:
            return False, []
        
        unavailable_items = []
        
        # Parse order items
        try:
            order_items = order.items if isinstance(order.items, list) else json.loads(order.items)
        except:
            order_items = order.items
        
        for item in order_items:
            # Get the menu item
            menu_item = MenuItem.query.filter_by(
                name=item.get('name'),
                restaurant_id=order.restaurant_id
            ).first()
            
            if not menu_item or not menu_item.available:
                unavailable_items.append({
                    'name': item.get('name'),
                    'quantity': item.get('quantity', 1),
                    'reason': 'Out of stock' if menu_item else 'Item not found'
                })
        
        return len(unavailable_items) == 0, unavailable_items

def mark_item_unavailable(menu_item_id, reason="Temporarily out of stock"):
    """
    Mark a menu item as unavailable and notify affected customers
    """
    with app.app_context():
        menu_item = MenuItem.query.get(menu_item_id)
        if not menu_item:
            return False
        
        # Mark item as unavailable
        menu_item.available = False
        db.session.commit()
        
        # Find all pending orders with this item
        pending_orders = Order.query.filter(
            Order.status.in_(['pending', 'confirmed']),
            Order.restaurant_id == menu_item.restaurant_id
        ).all()
        
        affected_orders = []
        for order in pending_orders:
            try:
                order_items = order.items if isinstance(order.items, list) else json.loads(order.items)
                for item in order_items:
                    if item.get('name') == menu_item.name:
                        affected_orders.append(order)
                        break
            except:
                continue
        
        # Notify affected customers
        for order in affected_orders:
            notify_customer_food_unavailable(order.id, menu_item.name, reason)
        
        return True

def mark_item_available(menu_item_id):
    """
    Mark a menu item as available
    """
    with app.app_context():
        menu_item = MenuItem.query.get(menu_item_id)
        if not menu_item:
            return False
        
        menu_item.available = True
        db.session.commit()
        return True

def notify_customer_food_unavailable(order_id, item_name, reason):
    """
    Notify customer that their ordered food is unavailable
    """
    with app.app_context():
        order = Order.query.get(order_id)
        if not order:
            return
        
        message = f"❌ **Order Update #{order.id}**\n\n"
        message += f"We're sorry to inform you that **{item_name}** is currently unavailable.\n\n"
        message += f"**Reason:** {reason}\n\n"
        message += "**Options:**\n"
        message += "• You can modify your order by removing this item\n"
        message += "• Choose a similar item from our menu\n"
        message += "• Cancel your order for a full refund\n\n"
        message += "Please contact us if you need assistance with your order."
        
        # Send notification to customer
        send_message(order.telegram_user_id, message)

def notify_customer_food_available(order_id):
    """
    Notify customer that their order is being prepared
    """
    with app.app_context():
        order = Order.query.get(order_id)
        if not order:
            return
        
        message = f"✅ **Order Confirmed #{order.id}**\n\n"
        message += f"Great news! All items in your order are available and we're preparing them now.\n\n"
        message += f"**Estimated preparation time:** 15-20 minutes\n"
        message += f"**Delivery time:** {order.estimated_delivery_time or '30-45 minutes'}\n\n"
        message += "We'll notify you once your order is ready for delivery!"
        
        # Send notification to customer
        send_message(order.telegram_user_id, message)

def process_order_availability_check(order_id):
    """
    Process an order and check food availability
    """
    with app.app_context():
        available, unavailable_items = check_food_availability(order_id)
        
        if available:
            # All items available - notify customer and update order status
            notify_customer_food_available(order_id)
            
            # Update order status to confirmed
            order = Order.query.get(order_id)
            if order:
                order.status = 'confirmed'
                db.session.commit()
                
        else:
            # Some items unavailable - notify customer
            order = Order.query.get(order_id)
            if order:
                unavailable_names = [item['name'] for item in unavailable_items]
                message = f"❌ **Order Issue #{order.id}**\n\n"
                message += "The following items are currently unavailable:\n\n"
                
                for item in unavailable_items:
                    message += f"• **{item['name']}** (Qty: {item['quantity']}) - {item['reason']}\n"
                
                message += f"\n**Available options:**\n"
                message += "• Modify your order\n"
                message += "• Choose alternative items\n"
                message += "• Cancel for full refund\n\n"
                message += "Please contact us to resolve this issue."
                
                send_message(order.telegram_user_id, message)
        
        return available, unavailable_items

def get_availability_summary(restaurant_id):
    """
    Get availability summary for a restaurant
    """
    with app.app_context():
        total_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).count()
        available_items = MenuItem.query.filter_by(restaurant_id=restaurant_id, available=True).count()
        unavailable_items = total_items - available_items
        
        return {
            'total_items': total_items,
            'available_items': available_items,
            'unavailable_items': unavailable_items,
            'availability_percentage': (available_items / total_items * 100) if total_items > 0 else 0
        }

def bulk_update_availability(restaurant_id, item_ids, available=True):
    """
    Bulk update availability for multiple items
    """
    with app.app_context():
        MenuItem.query.filter(
            MenuItem.id.in_(item_ids),
            MenuItem.restaurant_id == restaurant_id
        ).update({'available': available})
        
        db.session.commit()
        return True

if __name__ == "__main__":
    # Test the system
    with app.app_context():
        # Get availability summary for restaurant 1
        summary = get_availability_summary(1)
        print(f"Availability Summary: {summary}")