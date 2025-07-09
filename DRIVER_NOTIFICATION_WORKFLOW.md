# Driver Notification System - Complete Workflow

## Overview
The ET-FOOD driver notification system connects driver Telegram chat IDs with order assignments through an automated contact sharing workflow. Here's how it works:

## 1. Driver Registration & Contact Sharing

### When Driver Starts the Bot:
1. Driver messages the driver bot (@Food_Driver_Bot)
2. Bot requests contact sharing with button "📱 Share Contact"
3. Driver shares their phone number via Telegram contact
4. System automatically links driver account

### Contact Matching Process:
```python
# System searches for existing driver by phone number
clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '')
driver = Driver.query.filter(
    Driver.phone_number.like(f'%{clean_phone[-10:]}%')
).first()

if driver:
    # Link existing driver to Telegram account
    driver.telegram_user_id = chat_id
    db.session.commit()
```

## 2. Order Assignment Workflow

### Complete Flow:
1. **Customer** places order through Telegram WebApp
2. **Admin** confirms order in dashboard
3. **System** searches for nearby drivers (10km radius)
4. **Drivers** receive notifications via their Telegram chat IDs
5. **First driver** to accept gets the order

### Driver Search Algorithm:
```python
def find_nearby_drivers(self, order_id):
    # Find available drivers with recent location updates
    available_drivers = Driver.query.filter_by(
        is_active=True,
        is_available=True,
        is_approved=True
    ).filter(
        Driver.current_lat.isnot(None),
        Driver.current_lng.isnot(None),
        Driver.last_location_update > datetime.utcnow() - timedelta(minutes=10)
    ).all()
    
    # Calculate distances and sort by proximity
    for driver in available_drivers:
        distance = calculate_distance(restaurant_location, driver_location)
        if distance <= 10.0:  # Within 10km radius
            notify_driver_about_order(driver, order, distance)
```

## 3. Notification System

### Driver Notification Message:
```
🚚 NEW DELIVERY REQUEST 🚚

📋 Order #42
🏪 Restaurant: ET-FOOD Kitchen
📍 Distance to Restaurant: 2.5 km
📍 Distance to Customer: 3.1 km

👤 Customer: John Doe
📞 Phone: +251911000001
📍 Address: Bole, Addis Ababa
💰 Total Amount: 350.00 ETB
💳 Payment: telebirr

⏰ First to accept gets the order!
```

### Interactive Buttons:
- ✅ ACCEPT ORDER (accepts assignment)
- ❌ REJECT (declines assignment)
- 📞 Call Restaurant (direct calling)
- 📞 Call Customer (direct calling)

## 4. Status-Based Notifications

### Driver receives updates when:
- Order is **confirmed** → "New delivery request"
- Order is **preparing** → "Order being prepared"
- Order is **out_for_delivery** → "Order ready for pickup"
- Order is **delivered** → "Order completed, earnings calculated"

## 5. Location Requirements

### For Order Assignment:
- Driver must have shared location within last 10 minutes
- Location is used for distance calculations
- Only drivers within 10km radius receive notifications

### Location Sharing Process:
1. Driver shares contact → Account linked
2. Bot requests location sharing
3. Driver shares GPS coordinates
4. System stores location with timestamp
5. Driver becomes eligible for order assignments

## 6. Telegram Chat ID Integration

### How Chat IDs Connect:
```python
# When driver shares contact
driver.telegram_user_id = chat_id  # Links Telegram account

# When order is assigned
send_driver_message(driver.telegram_user_id, notification_message)
```

### Database Schema:
```sql
CREATE TABLE driver (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    telegram_user_id BIGINT UNIQUE,  -- Links to Telegram account
    current_lat FLOAT,
    current_lng FLOAT,
    last_location_update DATETIME,
    is_active BOOLEAN DEFAULT TRUE,
    is_available BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE
);
```

## 7. Complete System Architecture

### Components:
1. **Driver Bot** (@Food_Driver_Bot) - Handles driver interactions
2. **Contact Sharing** - Links phone numbers to Telegram IDs
3. **Location Tracking** - Manages driver GPS coordinates
4. **Order Assignment** - Finds nearby drivers automatically
5. **Notification System** - Sends order details to drivers

### Key Features:
- **Automatic linking** of driver accounts via phone numbers
- **Proximity-based** order assignment (10km radius)
- **Real-time notifications** with interactive buttons
- **Status tracking** throughout order lifecycle
- **Location requirements** for order eligibility

## 8. Testing the System

### To test the complete workflow:
1. Add drivers to admin dashboard with phone numbers
2. Drivers start driver bot and share contact
3. System automatically links accounts
4. Drivers share location to become eligible
5. Create test order and confirm in admin dashboard
6. System notifies nearest available drivers
7. Driver accepts order and receives status updates

This system ensures efficient driver dispatch based on proximity while maintaining seamless Telegram integration through contact sharing.