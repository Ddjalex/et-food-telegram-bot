import os

class Config:
    # Telegram Bot Configuration
    BOT_TOKEN = os.environ.get('ETFASTFOOD_BOT_TOKEN', 'your_bot_token_here')
    DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN', 'your_driver_bot_token_here')
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL', f'https://{os.environ.get("REPLIT_DEV_DOMAIN") or os.environ.get("RENDER_EXTERNAL_URL", "localhost").replace("https://", "")}')
    
    # Admin Configuration
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # App Configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'fallback_secret_key_for_dev')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///food_delivery.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
