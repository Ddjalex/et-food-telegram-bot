import os

class Config:
    # Telegram Bot Configuration
    BOT_TOKEN = os.environ.get('ETFASTFOOD_BOT_TOKEN', 'your_bot_token_here')
    DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN', 'your_driver_bot_token_here')
    @staticmethod
    def get_webhook_url():
        """Safely construct webhook URL with proper protocol handling"""
        # Get environment variables
        render_url = os.environ.get('RENDER_EXTERNAL_URL')
        replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
        custom_url = os.environ.get('WEBHOOK_URL')
        
        if custom_url:
            return custom_url
        
        # Choose the appropriate base URL
        if render_url:
            base_url = render_url
        elif replit_domain:
            base_url = replit_domain
        else:
            base_url = 'localhost'
        
        # Strip any existing protocol
        base_url = base_url.replace('https://', '').replace('http://', '')
        
        # Construct clean HTTPS URL
        return f"https://{base_url}"
    
    WEBHOOK_URL = get_webhook_url()
    
    # Admin Configuration
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # App Configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'fallback_secret_key_for_dev')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///food_delivery.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
