# ET-FOOD Telegram Bot System

## Overview
ET-FOOD is a comprehensive food delivery management system built with Flask and Telegram Bot integration. The system connects restaurants, customers, drivers, and administrators through automated workflows, featuring real-time order tracking, driver management, and payment processing.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes
- **July 31, 2025 - Complete MongoDB Migration**: Successfully migrated entire ET-FOOD delivery platform from PostgreSQL to MongoDB. Created custom MongoDB client (mongodb_client.py) to bypass PyMongo dependency conflicts. Implemented complete MongoDB models (models_final.py) with Restaurant, MenuItem, Order, Driver, AdminUser, PaymentTransaction, and Category models. Built comprehensive MongoDB Flask application (app_mongodb.py) with full CRUD functionality. All API endpoints working: /api/restaurant-info, /api/menu, /api/categories, /api/orders (GET/POST). Admin authentication functional with admin/admin123 and superadmin/superadmin123 credentials. Database pre-populated with 2 restaurants, 15 menu items across 5 categories, and 2 admin users. System now fully operational on MongoDB with the connection string: mongodb+srv://almeseged:A1l2m3e4s5@cluster0.t6sz6bo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0.

- **July 31, 2025 - Complete System Migration to Replit Environment**: Successfully completed migration from Replit Agent to standard Replit environment. Installed Python 3.11 with all required dependencies (Flask 3.1.1, SQLAlchemy 2.0.41, Gunicorn 23.0.0, python-telegram-bot 22.2, PyMongo 4.13.2, psycopg2-binary 2.9.10). Fixed JavaScript frontend issues with menu loading and item interaction. Resolved data structure conflicts in API responses. Application fully operational on port 5000 with complete MongoDB integration, working menu display with 15 items across 5 categories, functional add/remove cart system, and proper price display. All checklist items completed successfully. Restored original frontend interface as requested by user and integrated user's MongoDB Atlas connection string (mongodb+srv://almeseged:A1l2m3e4s5@cluster0.t6sz6bo.mongodb.net/).

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python)
- **Database**: MongoDB Atlas (production) with custom client implementation
- **Bot Framework**: python-telegram-bot for Telegram integration
- **Authentication**: Session-based with role-based access control
- **File Storage**: Local file system with static file serving
- **MongoDB Client**: Custom HTTP-based client avoiding PyMongo dependency conflicts

### Frontend Architecture
- **Templates**: Jinja2 templates with Bootstrap 5
- **UI Framework**: Bootstrap 5 with custom CSS
- **Maps**: OpenStreetMap with Leaflet.js for location tracking
- **Charts**: Chart.js for analytics dashboards
- **Real-time Updates**: AJAX polling for live data

### Database Design
- **Database**: MongoDB with custom model layer
- **Collections**: restaurants, menu_items, categories, orders, drivers, admin_users, payment_transactions
- **Models**: Restaurant, MenuItem, Category, Order, Driver, AdminUser, PaymentTransaction
- **Relationships**: String-based ID references between documents
- **Location Data**: GPS coordinates stored for drivers and delivery addresses
- **Document Structure**: JSON-based documents with UUID string IDs

## Key Components

### 1. Telegram Bot System
- **Customer Bot** (`@Etfastfood_bot`): Handles customer orders and tracking
- **Driver Bot** (`@Food_Driver_Bot`): Manages driver operations and notifications
- **WebApp Integration**: Telegram WebApp for menu browsing and ordering
- **Webhook Processing**: Real-time message processing via webhooks

### 2. Driver Management System
- **Registration Flow**: Contact sharing and document verification
- **Real-time Location**: GPS tracking with 10km radius assignment
- **Order Assignment**: Proximity-based automatic driver selection
- **Status Management**: Available/Busy state tracking
- **Approval Workflow**: Admin approval for new drivers

### 3. Admin Dashboard System
- **Multi-level Access**: Super admin, restaurant admin, kitchen staff roles
- **Order Management**: Real-time order tracking and status updates
- **Menu Management**: Item creation with image upload functionality
- **Driver Oversight**: Driver approval and monitoring tools
- **Payment Verification**: Transaction verification with receipt uploads

### 4. Kitchen Workflow System
- **Order Processing**: Kitchen staff can accept/reject orders
- **Status Updates**: Real-time communication with customers
- **Preparation Tracking**: Step-by-step cooking progress
- **Customer Notifications**: Automated updates via Telegram

### 5. Payment System
- **Multiple Methods**: Cash on delivery, bank transfer, mobile money
- **Receipt Verification**: Image upload and admin verification
- **Transaction Tracking**: Complete payment history and status
- **Automated Workflows**: Payment approval triggers order preparation

## Data Flow

### Order Workflow
1. **Customer Places Order**: Via Telegram WebApp interface
2. **Kitchen Acceptance**: Kitchen staff confirms item availability
3. **Payment Processing**: Customer submits payment with receipt
4. **Admin Verification**: Payment verification by restaurant admin
5. **Driver Assignment**: Automatic assignment to nearest available driver
6. **Delivery Tracking**: Real-time GPS tracking and status updates
7. **Order Completion**: Confirmation and rating collection

### Driver Assignment Flow
1. **Location Verification**: Driver must share live location
2. **Proximity Calculation**: System finds drivers within 10km radius
3. **Notification Dispatch**: Order sent to 3 nearest drivers
4. **First Response**: First driver to accept gets the order
5. **Status Updates**: Automatic status changes (available ↔ busy)

### Admin Management Flow
1. **Multi-restaurant Support**: Restaurant-specific admin access
2. **Driver Approval**: Document verification and approval workflow
3. **Order Monitoring**: Real-time order tracking across restaurants
4. **Payment Oversight**: Transaction verification and approval

## External Dependencies

### Required Services
- **Telegram Bot API**: Bot token configuration for customer and driver bots
- **PostgreSQL**: Production database (configurable)
- **File Storage**: Local static file serving for images

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (configured)
- `PGDATABASE`, `PGHOST`, `PGPASSWORD`, `PGPORT`, `PGUSER`: PostgreSQL credentials (configured)
- `BOT_TOKEN`: Customer bot token from @BotFather (needs configuration)
- `DRIVER_BOT_TOKEN`: Driver bot token from @BotFather (needs configuration)
- `SESSION_SECRET`: Flask session encryption key (has fallback)
- `WEBHOOK_URL`: External webhook URL for bot communication (optional)
- `RENDER_EXTERNAL_URL`: Render.com deployment URL (optional)
- `REPLIT_DEV_DOMAIN`: Replit development domain (auto-configured)
- `ADMIN_PASSWORD`: Admin dashboard password (defaults to admin123)

### Third-party Integrations
- **OpenStreetMap**: Location services and mapping
- **Telegram WebApp**: In-app web interface for customers
- **Payment Gateways**: Mobile money and bank transfer support

## Deployment Strategy

### Production Environment
- **Platform**: Render.com deployment ready
- **Database**: PostgreSQL with connection pooling
- **File Storage**: Static file serving with proper MIME types
- **Webhooks**: Automatic webhook registration on startup
- **Environment**: Production-specific configuration management

### Development Environment
- **Local Development**: SQLite database for rapid iteration
- **Hot Reload**: Flask development server with auto-restart
- **Debug Mode**: Comprehensive logging and error reporting
- **Test Data**: Automated test data creation scripts

### Migration Support
- **Database Migrations**: Automated schema updates
- **Data Persistence**: Backup and restore functionality
- **Git Workflow**: Safe deployment with data protection
- **Zero Downtime**: Rolling deployment capability

### Key Features for Code Agent
- **Modular Architecture**: Clear separation of concerns across files
- **Error Handling**: Comprehensive try-catch blocks with logging
- **Data Validation**: Input validation and sanitization throughout
- **Real-time Updates**: AJAX-based live data refresh
- **Mobile Responsive**: Bootstrap-based responsive design
- **Multi-language**: Template structure supports localization