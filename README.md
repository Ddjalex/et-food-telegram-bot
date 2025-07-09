# ET-FOOD - Telegram Food Delivery Bot

A comprehensive food delivery management system with advanced driver allocation and real-time order tracking capabilities.

## Features

### 🍕 Customer Experience
- **Telegram Bot Integration**: Interactive bot for menu browsing and ordering
- **WebApp Interface**: Modern web interface for product catalog and cart management
- **Multi-language Support**: English, Amharic, Oromo, Tigrinya
- **Live Location Sharing**: GPS-based delivery tracking
- **Order History**: Track past orders and reorder favorites
- **Payment Options**: Cash on Delivery, Bank Transfer, Mobile Money

### 🚚 Driver Management
- **Automatic Driver Assignment**: GPS-based proximity matching (10km radius)
- **Driver Bot**: Dedicated Telegram bot for delivery drivers
- **Real-time Location Tracking**: Live GPS updates every 30 seconds
- **Driver Approval System**: Admin approval workflow for new drivers
- **Order Assignment**: First-come-first-served order acceptance
- **Earnings Tracking**: Driver earnings and delivery statistics

### 👨‍💼 Admin Dashboard
- **Order Management**: Real-time order tracking and status updates
- **Menu Management**: Add/edit menu items with image upload
- **Category Management**: Organize products by categories
- **Driver Management**: Approve, remove, and monitor drivers
- **Analytics Dashboard**: Sales statistics and performance metrics
- **Live Tracking**: Real-time driver location monitoring

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (configurable to PostgreSQL)
- **Bot Framework**: python-telegram-bot
- **Frontend**: Bootstrap 5 with custom CSS
- **Maps**: OpenStreetMap with Leaflet.js
- **Charts**: Chart.js for analytics
- **File Storage**: Local file system with upload support

## Installation

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Driver Bot Token (separate bot for drivers)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/Ddjalex/et-food-telegram-bot.git
cd et-food-telegram-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Variables**
Create a `.env` file or set environment variables:
```bash
BOT_TOKEN=your_telegram_bot_token
DRIVER_BOT_TOKEN=your_driver_bot_token
SESSION_SECRET=your_session_secret
ADMIN_PASSWORD=your_admin_password
```

4. **Run the application**
```bash
python main.py
```

The application will start on `http://localhost:5000`

## Configuration

### Database Setup
The application uses SQLite by default. To use PostgreSQL:
```bash
DATABASE_URL=postgresql://user:password@localhost/etfood
```

### Webhook Configuration
For production deployment, set your webhook URL:
```bash
WEBHOOK_URL=https://yourdomain.com
```

## Usage

### For Customers
1. Start the bot: `/start`
2. Share contact information
3. Browse menu using WebApp
4. Add items to cart
5. Complete checkout with delivery details
6. Track order status

### For Drivers
1. Start the driver bot: `/start`
2. Share contact for account linking
3. Wait for admin approval
4. Share live location
5. Receive order notifications
6. Accept orders and complete deliveries

### For Admins
1. Access admin dashboard: `/admin`
2. Enter admin password
3. Manage orders, menu, and drivers
4. Monitor real-time analytics
5. Track driver locations

## API Endpoints

### Orders
- `GET /api/orders` - Get all orders (admin)
- `POST /api/orders` - Create new order
- `PUT /api/orders/{id}/status` - Update order status

### Menu
- `GET /api/menu` - Get menu items
- `POST /api/menu` - Add menu item (admin)
- `PUT /api/menu/{id}` - Update menu item (admin)

### Drivers
- `GET /api/drivers` - Get all drivers (admin)
- `POST /api/drivers/{id}/approve` - Approve driver (admin)
- `DELETE /api/drivers/{id}/remove` - Remove driver (admin)

### Categories
- `GET /api/categories` - Get all categories
- `POST /api/categories` - Create category (admin)

## Database Schema

### Key Tables
- **orders**: Customer orders with delivery details
- **menu_items**: Product catalog with pricing
- **drivers**: Driver profiles and status
- **categories**: Product categories
- **order_items**: Order line items

## Deployment

### Replit Deployment
1. Import project to Replit
2. Set environment secrets
3. Run with `gunicorn --bind 0.0.0.0:5000 main:app`

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
```

### Production Considerations
- Use PostgreSQL for production database
- Enable SSL/TLS for webhooks
- Configure Redis for session storage
- Set up monitoring and logging
- Use environment variables for sensitive data

## Menu Items

The system includes 62 menu items across 14 categories:
- Burgers (8 items)
- Shawarma (6 items)
- Sandwiches & Wraps (4 items)
- Pizza (8 items)
- Pasta (6 items)
- Borrito (4 items)
- Rice Dishes (4 items)
- Egg Dishes & Toast (6 items)
- Fries & Pancakes (4 items)
- Traditional Ethiopian Breakfast (4 items)
- Extras (4 items)
- Drinks (4 items)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please contact the development team or create an issue in the repository.

## Changelog

- **July 2025**: Initial release with complete delivery system
- **Enhanced Driver Management**: Added approval/removal system
- **Real-time Tracking**: GPS-based location sharing
- **Payment Integration**: Multiple payment methods
- **Admin Dashboard**: Comprehensive management interface