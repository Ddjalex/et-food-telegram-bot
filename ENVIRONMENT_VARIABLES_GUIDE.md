# ET-FOOD Environment Variables Guide

## Overview
This document lists all environment variables used throughout the ET-FOOD delivery system and their connections to .env configuration.

## Core Environment Variables

### Database Configuration
```
DATABASE_URL - PostgreSQL connection string (required for production)
PGDATABASE - PostgreSQL database name
PGHOST - PostgreSQL host
PGPASSWORD - PostgreSQL password  
PGPORT - PostgreSQL port
PGUSER - PostgreSQL username
```

### Telegram Bot Configuration
```
BOT_TOKEN - Main customer bot token from @BotFather
DRIVER_BOT_TOKEN - Driver bot token from @BotFather
ETFASTFOOD_BOT_TOKEN - Alternative customer bot token
```

### Web Application Configuration
```
SESSION_SECRET - Flask session encryption key
ADMIN_PASSWORD - Default admin password (fallback: admin123)
WEBHOOK_URL - Custom webhook URL for Telegram bots
```

### Deployment Environment Variables
```
RENDER_EXTERNAL_URL - Render.com deployment URL
REPLIT_DEV_DOMAIN - Replit development domain
```

## Files Using Environment Variables

### config.py - Main Configuration
```python
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token_here')
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN', 'your_driver_bot_token_here')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
SECRET_KEY = os.environ.get('SESSION_SECRET', 'fallback_secret_key_for_dev')
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///food_delivery.db')
```

### app.py - Flask Application
```python
app.secret_key = os.environ.get("SESSION_SECRET", "et-food-secret-key-2025-replit-migration-success")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
```

### url_utils.py - URL Construction
```python
render_url = os.environ.get('RENDER_EXTERNAL_URL')
webhook_url = os.environ.get('WEBHOOK_URL')
replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
```

### real_time_notifications.py - Telegram Notifications
```python
bot_token = os.environ.get('BOT_TOKEN', os.environ.get('ETFASTFOOD_BOT_TOKEN'))
```

### admin_routes.py - Admin Interface
```python
customer_bot_token = os.environ.get('ETFASTFOOD_BOT_TOKEN')
driver_bot_token = os.environ.get('DRIVER_BOT_TOKEN')
```

### driver_bot.py - Driver Bot System
```python
os.environ.get('RENDER_EXTERNAL_URL')
os.environ.get('WEBHOOK_URL')
```

### driver_integration_system.py - Driver Management
```python
self.driver_bot_token = os.environ.get('DRIVER_BOT_TOKEN')
os.environ.get('REPLIT_DEV_DOMAIN')
```

### driver_registration.py - Driver Registration
```python
DRIVER_BOT_TOKEN = os.environ.get('DRIVER_BOT_TOKEN')
os.environ.get('REPLIT_DEV_DOMAIN')
```

## Current .env File Status
The .env file is currently empty but can be populated with:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database

# Telegram Bot Tokens
BOT_TOKEN=your_customer_bot_token_here
DRIVER_BOT_TOKEN=your_driver_bot_token_here

# Security
SESSION_SECRET=your_secure_session_key_here
ADMIN_PASSWORD=your_admin_password_here

# Deployment
WEBHOOK_URL=https://your-domain.com
RENDER_EXTERNAL_URL=https://your-app.onrender.com
```

## Environment Variable Priority
1. **Production**: Values from actual environment variables
2. **Development**: Values from .env file (if configured)
3. **Fallback**: Default values in code

## Security Notes
- Never commit actual values to version control
- Use strong, unique values for SESSION_SECRET
- Bot tokens must be obtained from @BotFather on Telegram
- Database credentials should use connection pooling in production

## Available Environment Variables (Already Set)
The system currently has these PostgreSQL environment variables available:
- DATABASE_URL
- PGDATABASE  
- PGHOST
- PGPASSWORD
- PGPORT
- PGUSER

## Next Steps
To complete the configuration:
1. Obtain bot tokens from @BotFather
2. Set SESSION_SECRET to a secure random string
3. Configure WEBHOOK_URL for production deployment
4. Set ADMIN_PASSWORD for enhanced security