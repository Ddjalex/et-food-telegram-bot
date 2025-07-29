# ET-FOOD Login Credentials

## Super Admin Login
Access URL: http://localhost:5000/superadmin

### Credentials:
1. **Primary Super Admin**
   - Username: `admin`
   - Password: `admin123`
   - Role: super_admin

2. **Backup Super Admin**
   - Username: `superadmin`
   - Password: `superadmin123`
   - Role: super_admin

## Features Access:
- Restaurant Management
- Menu Management
- Order Management
- Driver Management
- System Settings
- Analytics & Reports

## Food Images Status:
✅ All 6 menu items now use real food images from static/uploads:
- Classic Burger: `/uploads/1751892160_22.JPG`
- Chicken Burger: `/uploads/1751892507_languge_2.jpg`
- Beef Shawarma: `/uploads/1751974703_Beef_Shawarama_Large.jpg`
- Mixed Platter: `/uploads/1751965845_Chicken_Burger_Special.jpg`
- French Fries: `/uploads/1751898445_st3.jpg`
- Coca Cola: `/uploads/1751974754_images_22.jpg`

## Flask Static File Configuration:
- Flask app configured with `static_folder='static'`
- Dedicated `/uploads/<filename>` route for image serving
- Both `/static/uploads/` and `/uploads/` paths working correctly
- All image URLs return HTTP 200 responses

Last Updated: July 29, 2025