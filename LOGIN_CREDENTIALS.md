# ET-FOOD LOGIN CREDENTIALS

## Super Admin Access
- **URL**: `/superadmin`
- **Username**: `superadmin`
- **Password**: `admin123`
- **Access**: Full system management, restaurant management, user management

## Customer Access
- **Telegram Bot**: Use the customer bot for ordering
- **WebApp**: Access through Telegram bot menu

## Driver Access  
- **Telegram Bot**: Use the driver bot for delivery management
- **Registration**: Drivers can register through the driver bot

## Database Information
- **Type**: PostgreSQL
- **Connection**: Via DATABASE_URL environment variable
- **Restaurants**: 2 active restaurants
  - Flavour cafe | E.Fabrica (64 menu items across 14 categories)
  - Y Factory Restaurant (10 menu items)
- **Total Menu Items**: 74 items across both restaurants
- **Categories**: 8 categories (4 per restaurant)

## Bot Configuration
- **Customer Bot Token**: BOT_TOKEN (configured)
- **Driver Bot Token**: DRIVER_BOT_TOKEN (configured)
- **Webhooks**: Both properly configured and operational

## Migration Status
✅ **COMPLETED SUCCESSFULLY**
- Flask application running on port 5000
- PostgreSQL database connected and populated
- Both Telegram bots operational
- Admin dashboard accessible
- WebApp interface functional