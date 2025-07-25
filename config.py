import os

class Config:
    # Telegram Bot Configuration
    BOT_TOKEN = os.environ.get('ETFASTFOOD_BOT_TOKEN', 'your_bot_token_here')
    DRIVER_BOT_TOKEN = os.environ.get('FOOD_DRIVER_BOT_TOKEN', 'your_driver_bot_token_here')
    @staticmethod
    def get_webhook_url():
        """Get webhook URL with fallback to custom URL if set"""
        custom_url = os.environ.get('WEBHOOK_URL')
        if custom_url:
            return custom_url
        
        from url_utils import construct_url
        return construct_url()
    
    WEBHOOK_URL = get_webhook_url()
    
    # Admin Configuration
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # App Configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'fallback_secret_key_for_dev')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///food_delivery.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
