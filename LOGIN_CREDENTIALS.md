# ET-FOOD Admin Login Credentials

## Super Admin Account
**Access Level**: Full system control, manage all restaurants and admins
- **Username**: superadmin
- **Password**: superadmin123
- **Login URL**: /superadmin
- **Permissions**: Create restaurants, manage all admins, system settings

## Restaurant Admin Accounts
**Access Level**: Restaurant-specific management

### Account 1 - Primary Admin
- **Username**: admin
- **Password**: admin123
- **Restaurant**: Flavour cafe | E.Fabrica
- **Login URL**: /admin

### Account 2 - Manager Account
- **Username**: flavour
- **Password**: flavour123
- **Restaurant**: Flavour cafe | E.Fabrica
- **Login URL**: /admin

## Access Structure

```
Super Admin (superadmin)
└── Can manage all restaurants and create new admins
    
Restaurant Admins (admin, flavour)
└── Can manage specific restaurant: Flavour cafe | E.Fabrica
    ├── Menu management (80 food items)
    ├── Order processing
    ├── Driver management
    └── Payment verification
```

## Current System Status
✅ **80 Food Items**: All authentic food images properly linked to menu  
✅ **Auto-Sync**: Menu automatically syncs across environments  
✅ **Admin Access**: All admin accounts active and approved  
✅ **Database**: PostgreSQL fully operational  
✅ **Web App**: Telegram WebApp displaying all food products  

## Navigation
- **Customer Interface**: Main webapp (Telegram WebApp)
- **Restaurant Admin**: /admin (for restaurant management)
- **Super Admin**: /superadmin (for system-wide control)
- **API Endpoints**: /api/menu, /api/restaurants/info (functional)

Your food delivery system is now fully operational with proper admin access!