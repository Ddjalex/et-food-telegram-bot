# ET-FOOD Telegram Bot System

## Overview
ET-FOOD is a comprehensive food delivery management system built with Flask and Telegram Bot integration. The system connects restaurants, customers, drivers, and administrators through automated workflows, featuring real-time order tracking, driver management, and payment processing.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes
- **July 31, 2025 - Migration Complete**: Successfully migrated ET-FOOD project from Replit Agent to Replit environment. All dependencies installed, PostgreSQL database created and configured, menu items and restaurants populated. Application now running successfully on port 5000 with full restaurant and menu functionality. Fixed superadmin login credentials (username: superadmin, password: admin123) and restored menu item placeholder images.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Bot Framework**: python-telegram-bot for Telegram integration
- **Authentication**: Session-based with role-based access control
- **File Storage**: Local file system with static file serving

### Frontend Architecture
- **Templates**: Jinja2 templates with Bootstrap 5
- **UI Framework**: Bootstrap 5 with custom CSS
- **Maps**: OpenStreetMap with Leaflet.js for location tracking
- **Charts**: Chart.js for analytics dashboards
- **Real-time Updates**: AJAX polling for live data

### Database Design
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Models**: Restaurant, MenuItem, Category, Order, Driver, AdminUser, PaymentTransaction
- **Relationships**: Foreign key relationships between orders, drivers, restaurants
- **Location Data**: GPS coordinates stored for drivers and delivery addresses

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
- `BOT_TOKEN`: Customer bot token from @BotFather
- `DRIVER_BOT_TOKEN`: Driver bot token from @BotFather
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Flask session encryption key
- `WEBHOOK_URL`: External webhook URL for bot communication

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