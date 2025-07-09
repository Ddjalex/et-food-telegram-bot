# ET-FOOD - Telegram Food Delivery Bot

## Overview

ET-FOOD is a Telegram-based food delivery application that combines a Python Flask web backend with a Telegram bot interface. The system allows customers to browse a menu, place orders through a Telegram WebApp, and enables restaurant administrators to manage orders and menu items through a web dashboard.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite (configurable to other databases)
- **Bot Integration**: python-telegram-bot library for Telegram API interaction
- **Session Management**: Flask sessions with configurable secret keys
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

### Frontend Architecture
- **Admin Dashboard**: Server-side rendered HTML templates with Bootstrap
- **Customer Interface**: Telegram WebApp using vanilla JavaScript
- **Styling**: Bootstrap with custom CSS and Font Awesome icons
- **Responsive Design**: Mobile-first approach optimized for Telegram's mobile interface

## Key Components

### Models (Database Schema)
1. **MenuItem**: Stores menu items with pricing, descriptions, and availability
2. **Order**: Comprehensive order management with customer details, items, and status tracking
3. **AdminUser**: User authentication for admin access (referenced but not fully implemented)

### Bot Integration
- **Webhook-based**: Receives updates via HTTP webhooks rather than polling
- **Command Handlers**: `/start`, `/menu`, `/track`, `/admin`, `/orders`, `/menuadmin`
- **Callback Handlers**: Interactive button responses
- **WebApp Integration**: Seamless integration with Telegram's WebApp feature

### API Endpoints
- **GET /api/menu**: Retrieve available menu items
- **GET /api/orders**: Admin endpoint for order management with pagination
- **POST /api/orders**: Submit new orders from customers
- **Various admin endpoints**: Order status updates, menu management, analytics

## Data Flow

1. **Customer Journey**:
   - Customer interacts with Telegram bot
   - Bot presents menu or opens WebApp
   - Customer selects items and fills order details
   - Order submitted via API to Flask backend
   - Order stored in database
   - Admin receives notification

2. **Admin Workflow**:
   - Admin accesses web dashboard
   - Views pending orders with customer details
   - Updates order status (pending → confirmed → preparing → delivered)
   - Manages menu items (add/edit/disable)
   - Exports order data for analysis

3. **Real-time Updates**:
   - Bot sends notifications to customers about order status
   - Admin dashboard refreshes order status
   - Location tracking for delivery coordination

## External Dependencies

### Python Packages
- **Flask**: Web framework and routing
- **SQLAlchemy**: Database ORM and migrations
- **python-telegram-bot**: Telegram Bot API integration
- **Werkzeug**: WSGI utilities and middleware

### Frontend Dependencies
- **Bootstrap**: UI framework and responsive design
- **Font Awesome**: Icon library
- **Telegram WebApp JS**: Official Telegram WebApp integration

### External Services
- **Telegram Bot API**: Primary interface for customer interactions
- **Unsplash**: Image hosting for menu item photos
- **Location Services**: GPS coordinates for delivery tracking

## Deployment Strategy

### Environment Configuration
- **Development**: SQLite database, debug mode enabled
- **Production**: Environment variables for sensitive data (BOT_TOKEN, ADMIN_PASSWORD)
- **Scalability**: Configurable database URI supports PostgreSQL, MySQL, etc.

### Deployment Requirements
- **Port Configuration**: Flexible port binding (default 5000)
- **Webhook Setup**: Requires public URL for Telegram webhook
- **SSL/TLS**: HTTPS required for Telegram WebApp functionality
- **Session Management**: Secure session keys for admin authentication

### Database Management
- **Auto-initialization**: Database tables created automatically on startup
- **Default Data**: Sample menu items populated if database is empty
- **Migration Support**: SQLAlchemy provides schema evolution capabilities

## Changelog
- July 05, 2025. Initial setup
- July 05, 2025. Fixed Telegram bot integration - bot now responds to all commands (/start, /menu, /track, /admin)
- July 05, 2025. Enhanced bot features: Contact sharing, location sharing, admin status notifications, customer status updates
- July 05, 2025. Added map view for admin dashboard - displays delivery locations with OpenStreetMap integration and external map app links for driver assistance
- July 05, 2025. Added file upload functionality for menu item images - supports JPG, PNG, GIF, WebP formats with fallback to URL input
- July 07, 2025. **MAJOR UPDATE**: Migrated to modern dark theme bot interface with category-based navigation (Burgers, Snacks, Sauces, Drinks), UZS currency support, improved WebApp design, multi-language support (English, Amharic, Oromo, Tigrinya), and enhanced user experience matching modern food delivery apps
- July 07, 2025. **FEATURE UPDATE**: Added live location sharing support, categories management in admin panel, driver management system with assignment functionality, and enhanced order tracking with driver assignment capabilities
- July 07, 2025. **MAJOR DRIVER SYSTEM**: Implemented comprehensive driver document verification with file attachments (license, ID, vehicle registration), admin approval/rejection system with reasons, live driver location tracking, driver notification system for order assignments with accept/decline options, and real-time location updates for customers tracking their deliveries
- July 07, 2025. **UI IMPROVEMENTS**: Changed currency from UZS to ETB (Ethiopian Birr) with proper conversion rates (1 USD ≈ 60 ETB), added interactive user profile system with Telegram integration, profile modal with user information display, and clickable profile section in header
- July 07, 2025. **CART SYSTEM**: Implemented comprehensive shopping cart functionality with floating cart button, cart modal with item management, checkout flow, order history access, real-time cart updates, and enhanced user experience with multiple cart access points
- July 07, 2025. **ADMIN ENHANCEMENT**: Completely redesigned admin dashboard with professional sidebar navigation, gradient design, statistics cards, interactive charts (Chart.js), real-time analytics, modern table containers, enhanced order management, and comprehensive dashboard overview with sales tracking
- July 07, 2025. **CART SYSTEM & ORDER HISTORY**: Added comprehensive shopping cart functionality with floating cart button, item management, checkout modal, and order history viewer. Fixed JavaScript errors for better Telegram WebApp compatibility. Orders now properly submit to admin dashboard with real-time updates.
- July 07, 2025. **MIGRATION TO REPLIT**: Successfully migrated project from Replit Agent to Replit environment with full functionality preservation. Added manual payment options (Cash on Delivery, Bank Transfer, Mobile Money) with complete checkout flow including order summary, customer information form, and payment method selection. Enhanced user interface with clickable cart info for seamless checkout experience.
- July 07, 2025. **LIVE LOCATION TRACKING**: Added share live location feature in checkout modal under delivery address field. Users can now share their real-time GPS coordinates for accurate delivery tracking. Location data is automatically included in order submissions and integrated with Telegram WebApp location sharing functionality.
- July 07, 2025. **TELEGRAM PROFILE PICTURES**: Integrated Telegram user profile photo display functionality. The app now attempts to load and display actual Telegram profile pictures in both header avatar and profile modal, with fallback to text-based avatars when photos are unavailable. Multiple photo access methods implemented including Telegram's public photo URLs and WebApp API integration.
- July 07, 2025. **ADMIN DASHBOARD OVERHAUL**: Completely rebuilt admin dashboard with modern gradient design, fixed all JavaScript errors, and implemented comprehensive management functionality. Added file upload system for menu item images replacing URL input, created modal-based forms for adding/editing menu items with image preview, enhanced categories management with full CRUD operations, and streamlined driver management system.
- July 07, 2025. **MIGRATION TO REPLIT COMPLETED**: Successfully migrated project from Replit Agent to Replit environment with full functionality preservation. Fixed Flask app structure for Replit compatibility, updated database configuration with proper environment variables, added comprehensive null checks in JavaScript to prevent errors, fixed order submission API to include required telegram_user_id field, and resolved Telegram WebApp version compatibility issues for showAlert method. All features now working properly including category loading, product display, cart functionality, and order placement.
- July 07, 2025. **USER PROFILE INTEGRATION FIXED**: Resolved "undefined undefined" profile display issue by implementing proper Telegram WebApp user data handling with fallback mechanisms. Enhanced profile avatar display with user initials, added cache-busting headers, and improved profile photo loading from Telegram. Successfully tested with real user data showing proper name and phone number display. Live location sharing functionality confirmed working with GPS coordinates properly stored in orders.
- July 07, 2025. **PAYMENT TRANSACTION SYSTEM**: Added comprehensive payment transaction tracking with transaction ID and image upload functionality for each payment method (CBE Birr, M-Pesa, Bank Transfer). Users can now upload payment screenshots during checkout, admin dashboard displays transaction details and images, implemented payment verification system with transaction ID validation, and added modal viewers for payment screenshots. Database schema updated with transaction_id and transaction_image_url columns for complete payment audit trail.
- July 07, 2025. **PROFILE DISPLAY FIX**: Fixed user profile display issue where "undefined undefined" was showing instead of proper user names. Enhanced Telegram WebApp user data loading with proper fallback handling, added cache-busting headers to prevent browser caching issues, improved profile avatar generation using user initials, and implemented comprehensive error handling for missing Telegram user data. Profile section now shows proper user information with fallback to "Demo User" when Telegram data is unavailable.
- July 07, 2025. **INTERACTIVE BOT RESTORATION**: Fully restored interactive Telegram bot functionality with contact sharing, inline keyboards, and WebApp integration. Added phone number collection with contact sharing buttons, category navigation (Burgers, Snacks, Sauces, Drinks), main menu with Catalog/Cart/Settings/Review options, WebApp integration for full product browsing, location sharing capabilities, and comprehensive callback handling. Bot now matches the original interactive interface shown in screenshots with proper keyboard layouts and user flow.
- July 08, 2025. **REPLIT MIGRATION COMPLETED**: Successfully migrated project from Replit Agent to Replit environment with full functionality preservation. Fixed all compatibility issues, cleaned up dependencies, and ensured proper Flask app structure for Replit deployment.
- July 08, 2025. **COMPLETE MENU OVERHAUL**: Added comprehensive menu from PDF with 62 menu items across 11 categories including Burgers, Shawarma, Sandwiches & Wraps, Pizza, Pasta, Borrito, Rice Dishes, Egg Dishes & Toast, Fries & Pancakes, Traditional Ethiopian Breakfast, and Extras. All items include proper pricing in ETB (Ethiopian Birr) and descriptions. Categories properly structured with icons and sort orders for optimal user experience.
- July 08, 2025. **REPLIT MIGRATION COMPLETED**: Successfully migrated ET-FOOD project from Replit Agent to Replit environment. Fixed all compatibility issues, installed required packages, configured BOT_TOKEN secret, and verified full functionality. Flask web server running on port 5000, SQLite database with 62 menu items operational, Telegram bot responding to commands with contact/location sharing working properly. All features preserved including admin dashboard, WebApp interface, and order management system.
- July 08, 2025. **ENHANCED BOT FLOW**: Improved bot user experience after contact and location sharing. After users share their phone number and location, they now see inline buttons for "Open Menu" (opens WebApp) and "Leave Feedback" (optional feedback system). Added comprehensive feedback system where users can send messages to admins, with cancel functionality and proper flow management. Feedback messages include user details and are sent to all registered admins.
- July 08, 2025. **CART PRICING FIX**: Fixed critical pricing bug in WebApp cart system. The inline JavaScript in webapp_modern_fixed.html was incorrectly multiplying prices by 60 (legacy USD to ETB conversion) causing cart prices to be 60x higher than menu prices. Removed incorrect currency conversion since database prices are already in ETB. Cart prices now match menu item prices correctly.
- July 08, 2025. **COMPREHENSIVE PRICING FIX**: Fixed all remaining currency conversion issues in webapp_modern.html file. Removed all incorrect multipliers (12000x) and UZS currency references, replaced with proper ETB display. Cart pricing now shows accurate amounts across all template files. System fully functional with correct Ethiopian Birr pricing throughout.
- July 08, 2025. **DELIVERY BOT SYSTEM**: Added automated delivery bot functionality that can be assigned from admin panel. Bot automatically accepts orders, sends notifications to customers, and handles delivery workflow without human intervention. Admin dashboard now includes "Assign Delivery Bot" and "Assign Human Driver" options in order management. Enhanced Telegram bot with proper callback handling for bot assignments and driver notifications. System creates delivery bot driver entry automatically when first assigned.
- July 08, 2025. **LIVE LOCATION TRACKING SYSTEM**: Implemented comprehensive live location sharing system for drivers and admin monitoring. Added real-time GPS tracking with 30-second updates, interactive live tracking map with driver markers, automated location updates for delivery bot with simulated route progression, admin dashboard with live tracking statistics and "View Map" button, driver location request system via Telegram, and enhanced bot notifications for location sharing. System includes full integration between human drivers and delivery bot with separate tracking workflows.
- July 08, 2025. **REPLIT MIGRATION RESTORED**: Successfully completed migration from Replit Agent to Replit environment. Fixed merge conflict markers in templates and JavaScript files, restored complete database with 14 food categories and 62 menu items, resolved WebApp functionality with proper Telegram integration, and cleaned up project structure. All core features working: web interface, admin dashboard, menu display, and order management. Bot functionality requires BOT_TOKEN environment variable to be configured.
- July 08, 2025. **REPLIT MIGRATION COMPLETED**: Successfully migrated ET-FOOD project from Replit Agent to Replit environment. Fixed all merge conflicts, restored 14 food categories and 62 menu items, cleaned up code structure, and verified web application functionality. Flask server running on port 5000, admin dashboard operational, WebApp interface working properly. Note: BOT_TOKEN environment variable needs to be reconfigured for Telegram bot functionality.
- July 08, 2025. **SIMPLIFIED BOT FLOW**: Streamlined bot user experience to eliminate duplicate messages and unnecessary steps. New flow: /start → share contact → direct WebApp menu access. Removed mandatory location sharing requirement, making the ordering process faster and more user-friendly. Bot now immediately shows "🍽️ Open Menu" WebApp button after contact sharing.
- July 08, 2025. **ORDER HISTORY FEATURE**: Implemented comprehensive order history functionality in WebApp with professional modal interface. Features include: pending orders display with color-coded status badges, order details (date, payment method, items, total), status-based action buttons (Cancel, Track, Reorder), real-time order management with API integration, and enhanced user experience with loading states and error handling. Fixed API endpoint path discrepancy for proper order loading.
- July 08, 2025. **REPLIT MIGRATION COMPLETED**: Successfully migrated ET-FOOD project from Replit Agent to Replit environment. All packages installed, Flask server running on port 5000, database operational with 14 categories and 62 menu items. Web interface fully functional with compact order history display optimized for mobile WebApp. Fixed API endpoints and enhanced order history UI with minimal, space-efficient design. Ready for deployment and development.
- July 08, 2025. **REPLIT MIGRATION COMPLETED**: Successfully migrated ET-FOOD project from Replit Agent to Replit environment. All functionality preserved including Flask web server on port 5000, SQLite database with 62 menu items, Telegram WebApp integration, admin dashboard, order management system. Fixed order history display with compact, thin design for better mobile viewing. All packages installed and verified working properly.
- July 08, 2025. **DRIVER BOT SYSTEM**: Created comprehensive driver bot system with separate Telegram bot (DRIVER_BOT_TOKEN) for delivery drivers. Features include: dedicated driver bot with webhook integration, mini web interface for order management showing restaurant details and distance calculations, accept/reject order functionality with real-time updates, integration with existing live location tracking system, fallback to main bot if driver bot unavailable, mobile-optimized driver panel with WebApp interface, distance calculations between restaurant and customer locations, direct calling links for restaurant and customer contact.
- July 08, 2025. **REPLIT MIGRATION FINAL**: Successfully completed migration from Replit Agent to Replit environment. All functionality fully operational including Flask web server on port 5000, SQLite database with 62 menu items across 14 categories, Telegram bot tokens configured (BOT_TOKEN and DRIVER_BOT_TOKEN), WebApp interface with proper Telegram integration, admin dashboard with order management, and driver bot system. Project ready for development and deployment.
- July 09, 2025. **MIGRATION COMPLETED**: Successfully migrated ET-FOOD project from Replit Agent to Replit environment. Fixed all Git merge conflicts in routes.py and driver_bot.py, resolved syntax errors, configured Telegram bot tokens (BOT_TOKEN and DRIVER_BOT_TOKEN), verified both customer and driver bots are working properly with webhook integration. Flask web application running on port 5000, database operational, WebApp interface functional. All core features preserved and operational.
<<<<<<< HEAD
- July 08, 2025. **ENHANCED ORDER MANAGEMENT**: Fixed admin dashboard clear orders functionality and added comprehensive time-based clearing options. Features include individual delete buttons for completed orders (delivered/cancelled), time-based bulk clearing (1 hour, 24 hours, 7 days, delete all), proper error handling with detailed logging, enhanced confirmation messages, and comprehensive API endpoints for both individual and bulk order deletion. Admin can now efficiently manage order history with precise control over what gets cleared.
=======
>>>>>>> 8611b9ea4616cb4851f0b48c3c11297c40c1d7f0
- July 08, 2025. **DRIVER BOT SYSTEM FIXED**: Fixed driver bot integration issues that were preventing proper order assignment notifications. Updated driver assignment flow to use dedicated driver bot (DRIVER_BOT_TOKEN) instead of main bot, added new API endpoint `/api/drivers/telegram/{telegram_user_id}/orders` to load driver orders by Telegram user ID, fixed driver panel JavaScript to properly detect drivers from Telegram WebApp user data, tested complete flow with real driver notification and order assignment. Driver bot now properly notifies drivers about order assignments and driver panel displays active orders correctly.
- July 08, 2025. **AUTOMATIC DRIVER DISPATCH SYSTEM**: Implemented automatic driver notification system that triggers when customers place orders. System finds nearest 3 available drivers using GPS coordinates, calculates distances, and notifies them via driver bot about new delivery requests. Features include: distance-based driver selection, automatic notifications with order details (customer info, payment method, distance), first-come-first-served order acceptance system, background processing to avoid blocking order creation, comprehensive error handling and logging. Drivers receive notifications instantly when orders are placed, can accept orders through driver panel or quick buttons, and system prevents double-assignment. Admin retains control over driver locations and monitoring features.
- July 08, 2025. **ADMIN LIVE DRIVER STATUS CONTROL**: Created comprehensive admin interface for real-time driver management and monitoring. Features include: dedicated "Drivers" tab in admin dashboard with live status cards showing total/active/available/busy drivers, real-time driver table with individual status controls (active/inactive toggle, available/busy toggle), location tracking with "View Location" buttons opening Google Maps, automatic status notifications sent to drivers via driver bot, 30-second auto-refresh for live monitoring, individual driver location requests, live tracking map showing all driver positions, driver action buttons for play/pause/location requests, and comprehensive error handling. Admin can now control driver availability in real-time and monitor their locations for efficient dispatch management.
- July 08, 2025. **ADD DRIVER EMPLOYEE SYSTEM**: Implemented complete "Add Driver Employee" functionality in admin dashboard for easy driver onboarding. Features include: modal form with driver details (name, phone, Telegram ID, vehicle type), auto-approval option for immediate activation, phone number auto-formatting with +251 prefix, duplicate Telegram ID validation, automatic welcome message sent via driver bot with system instructions, driver status commands (/start, /help, /status), comprehensive error handling with user-friendly messages, and real-time driver table refresh after adding. Admin can now easily add new drivers who instantly receive access to the driver bot system with welcome instructions and status tracking capabilities.
- July 08, 2025. **ADMIN DASHBOARD CLEANUP**: Fixed duplicate "Drivers" tab in admin navigation that was causing UI confusion. Removed redundant drivers tab section while preserving the main comprehensive drivers management interface with live status control, employee addition, and real-time tracking capabilities. Admin dashboard now has clean single navigation with all functionality intact.
<<<<<<< HEAD
- July 08, 2025. **REPLIT MIGRATION COMPLETED**: Successfully migrated ET-FOOD project from Replit Agent to Replit environment. All packages installed, both BOT_TOKEN and DRIVER_BOT_TOKEN configured, Flask web server running on port 5000, database operational with 62 menu items across 14 categories. Both main customer bot and driver bot webhooks properly configured and functional. WebApp interface and driver panel both working properly for mini web functionality. All core features preserved including order management, admin dashboard, and real-time driver dispatch system.
- July 08, 2025. **MANDATORY DRIVER LOCATION SHARING**: Implemented mandatory location sharing system for drivers to ensure nearby order assignments. Features include: driver bot welcome message emphasizing location sharing requirement, only drivers with location updates in last 10 minutes receive order assignments, location sharing status indicators in admin dashboard (Active/Outdated/Inactive), automated admin notifications when no drivers with current location are available, enhanced driver status command showing location sharing status with action buttons, automatic location update handling via driver bot webhook, and comprehensive location sharing request system with live location instructions. System ensures efficient driver dispatch based on proximity while maintaining real-time tracking capabilities.
=======
>>>>>>> 8611b9ea4616cb4851f0b48c3c11297c40c1d7f0

## User Preferences

Preferred communication style: Simple, everyday language.