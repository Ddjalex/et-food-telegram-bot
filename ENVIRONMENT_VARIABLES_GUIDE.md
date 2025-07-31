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
For security reasons, Replit doesn't allow direct editing of .env files. Instead:

1. **Environment Variables Template**: See `.env.template` for all available variables
2. **Replit Secrets**: Use Replit's built-in secrets manager for sensitive values
3. **Auto-configured**: Database variables are already set up in the environment

### Required Environment Variables for Full Functionality:
```env
# Critical for Telegram bot functionality
BOT_TOKEN=your_customer_bot_token_here
DRIVER_BOT_TOKEN=your_driver_bot_token_here

# Enhanced security (optional - has fallbacks)
SESSION_SECRET=your_secure_session_key_here
ADMIN_PASSWORD=your_admin_password_here

# Production deployment (optional)
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

## How to Configure Environment Variables in Replit

### Method 1: Using Replit Secrets (Recommended)
1. Go to your Replit project settings
2. Navigate to the "Secrets" tab
3. Add key-value pairs for sensitive variables like:
   - `BOT_TOKEN`
   - `DRIVER_BOT_TOKEN`
   - `SESSION_SECRET`

### Method 2: Using .env.template
1. Copy `.env.template` to `.env` locally (if working outside Replit)
2. Fill in your actual values
3. Never commit the actual .env file to version control

### Current Status
- **Database**: ✅ Already configured (PostgreSQL ready)
- **Web Application**: ✅ Working with fallback values
- **Bot Integration**: ⚠️ Needs bot tokens for full functionality
- **Security**: ✅ Has secure fallbacks, can be enhanced

### Next Steps
1. Get bot tokens from @BotFather on Telegram
2. Add tokens to Replit Secrets or use the provided ask_secrets tool
3. Configure WEBHOOK_URL for production deployment (optional)
4. Test bot functionality with real tokens