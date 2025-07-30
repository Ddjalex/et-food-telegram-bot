import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from flask import request, jsonify
from models import MenuItem, Order, AdminUser
from app import db
from config import Config
import asyncio

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global bot application
bot_app = None

def init_bot(flask_app):
    """Initialize the Telegram bot with Flask app context"""
    global bot_app
    
    if not Config.BOT_TOKEN or Config.BOT_TOKEN == 'your_bot_token_here':
        logger.error("BOT_TOKEN not configured properly")
        return
    
    try:
        bot_app = Application.builder().token(Config.BOT_TOKEN).build()
        
        # Add handlers
        bot_app.add_handler(CommandHandler("start", start_command))
        bot_app.add_handler(CommandHandler("menu", menu_command))
        bot_app.add_handler(CommandHandler("track", track_command))
        bot_app.add_handler(CommandHandler("admin", admin_command))
        bot_app.add_handler(CommandHandler("orders", orders_command))
        bot_app.add_handler(CommandHandler("menuadmin", menu_admin_command))
        bot_app.add_handler(CallbackQueryHandler(button_callback))
        
        logger.info("Bot initialized successfully")
        
        # Set up webhook
        setup_webhook(flask_app)
        
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")

def setup_webhook(flask_app):
    """Set up webhook for the bot"""
    try:
        webhook_url = f"{Config.WEBHOOK_URL}/webhook"
        
        # Create webhook route
        @flask_app.route('/webhook', methods=['POST'])
        def webhook():
            try:
                if bot_app:
                    update = Update.de_json(request.get_json(force=True), bot_app.bot)
                    asyncio.run(bot_app.process_update(update))
                return jsonify({'status': 'ok'})
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        # Set webhook
        asyncio.run(set_webhook_async(webhook_url))
        logger.info(f"Webhook set up at: {webhook_url}")
        
    except Exception as e:
        logger.error(f"Failed to set up webhook: {e}")

async def set_webhook_async(webhook_url):
    """Set webhook asynchronously"""
    try:
        await bot_app.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set successfully: {webhook_url}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome_message = f"""
🍕 Welcome to ET-FOOD, {user.first_name}! 🍕

Your favorite food delivery service is here to serve you delicious meals right to your doorstep!

🍔 What would you like to do?
• View our menu
• Place an order
• Track your order

Choose an option below:
"""
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("🍽️ View Menu", callback_data="view_menu")],
        [InlineKeyboardButton("🛒 Order Now", web_app=WebAppInfo(url=f"{Config.WEBHOOK_URL}/webapp"))],
        [InlineKeyboardButton("📦 Track Order", callback_data="track_order")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command"""
    with db.session.begin():
        menu_items = MenuItem.query.filter_by(available=True).all()
    
    if not menu_items:
        await update.message.reply_text("Sorry, no items available right now. Please check back later!")
        return
    
    menu_text = "🍽️ *Our Menu* 🍽️\n\n"
    
    for item in menu_items:
        menu_text += f"*{item.name}* - ${item.price:.2f}\n"
        menu_text += f"_{item.description}_\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🛒 Order Now", web_app=WebAppInfo(url=f"{Config.WEBHOOK_URL}/webapp"))]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(menu_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /track command"""
    user_id = update.effective_user.id
    
    with db.session.begin():
        recent_orders = Order.query.filter_by(telegram_user_id=user_id).order_by(Order.created_at.desc()).limit(3).all()
    
    if not recent_orders:
        await update.message.reply_text("You have no recent orders to track.")
        return
    
    message = "📦 *Your Recent Orders* 📦\n\n"
    
    for order in recent_orders:
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'preparing': '👨‍🍳',
            'delivered': '🎉',
            'cancelled': '❌'
        }.get(order.status, '📦')
        
        message += f"*Order #{order.id}*\n"
        message += f"Status: {status_emoji} {order.status.title()}\n"
        message += f"Total: ${order.total_amount:.2f}\n"
        message += f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    if not context.args:
        await update.message.reply_text("Please provide admin password: /admin <password>")
        return
    
    password = context.args[0]
    if password != Config.ADMIN_PASSWORD:
        await update.message.reply_text("❌ Invalid admin password!")
        return
    
    # Add user as admin
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    with db.session.begin():
        admin = AdminUser.query.filter_by(telegram_user_id=user_id).first()
        if not admin:
            admin = AdminUser(telegram_user_id=user_id, username=username)
            db.session.add(admin)
            db.session.commit()
    
    keyboard = [
        [InlineKeyboardButton("📊 View Orders", callback_data="admin_orders")],
        [InlineKeyboardButton("🍽️ Manage Menu", callback_data="admin_menu")],
        [InlineKeyboardButton("📈 Admin Dashboard", url=f"{Config.WEBHOOK_URL}/admin")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("✅ Admin access granted!\n\nChoose an option:", reply_markup=reply_markup)

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /orders command for admins"""
    user_id = update.effective_user.id
    
    with db.session.begin():
        admin = AdminUser.query.filter_by(telegram_user_id=user_id, is_active=True).first()
    
    if not admin:
        await update.message.reply_text("❌ Admin access required!")
        return
    
    with db.session.begin():
        orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        await update.message.reply_text("No orders found.")
        return
    
    message = "📋 *Recent Orders* 📋\n\n"
    
    for order in orders:
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'preparing': '👨‍🍳',
            'delivered': '🎉',
            'cancelled': '❌'
        }.get(order.status, '📦')
        
        message += f"*Order #{order.id}*\n"
        message += f"Customer: {order.customer_name}\n"
        message += f"Phone: {order.customer_phone}\n"
        message += f"Status: {status_emoji} {order.status.title()}\n"
        message += f"Total: ${order.total_amount:.2f}\n"
        message += f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def menu_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menuadmin command for admins"""
    user_id = update.effective_user.id
    
    with db.session.begin():
        admin = AdminUser.query.filter_by(telegram_user_id=user_id, is_active=True).first()
    
    if not admin:
        await update.message.reply_text("❌ Admin access required!")
        return
    
    with db.session.begin():
        menu_items = MenuItem.query.all()
    
    message = "🍽️ *Menu Management* 🍽️\n\n"
    
    for item in menu_items:
        status = "✅" if item.available else "❌"
        message += f"*{item.name}* {status}\n"
        message += f"Price: ${item.price:.2f}\n"
        message += f"Description: {item.description}\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "view_menu":
        await menu_command(update, context)
    elif query.data == "track_order":
        await track_command(update, context)
    elif query.data == "admin_orders":
        await orders_command(update, context)
    elif query.data == "admin_menu":
        await menu_admin_command(update, context)

def send_order_notification(order_id):
    """Send order notification to admins"""
    try:
        with db.session.begin():
            order = Order.query.get(order_id)
            admins = AdminUser.query.filter_by(is_active=True).all()
        
        if not order or not admins:
            return
        
        message = f"🆕 *New Order #{order.id}*\n\n"
        message += f"Customer: {order.customer_name}\n"
        message += f"Phone: {order.customer_phone}\n"
        message += f"Address: {order.customer_address}\n"
        message += f"Total: ${order.total_amount:.2f}\n"
        message += f"Payment: {order.payment_method}\n\n"
        
        # Add order items
        message += "*Items:*\n"
        for item in order.items:
            message += f"• {item['name']} x{item['quantity']} - ${item['price']:.2f}\n"
        
        # Send to all admins
        for admin in admins:
            try:
                asyncio.run(send_message_to_admin(admin.telegram_user_id, message))
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin.telegram_user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Failed to send order notification: {e}")

async def send_message_to_admin(user_id, message):
    """Send message to specific admin"""
    try:
        await bot_app.bot.send_message(chat_id=user_id, text=message, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Failed to send message to {user_id}: {e}")
