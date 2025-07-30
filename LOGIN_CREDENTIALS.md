# ET-FOOD Login Credentials

## Super Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: Super Administrator (Access to all restaurants)
- **Status**: ✅ Active and Ready

## Restaurant Admin Accounts
### Flavour Cafe Admin
- **Username**: `flavour`
- **Password**: `flavour123`
- **Role**: Restaurant Administrator (Flavour Cafe only)
- **Restaurant**: Flavour cafe | E.Fabrica
- **Status**: ✅ Active and Ready

### Test Restaurant Admin
- **Username**: `test_restaurant_admin`
- **Password**: `test123`
- **Role**: Restaurant Administrator (Flavour Cafe only)
- **Restaurant**: Flavour cafe | E.Fabrica
- **Status**: ✅ Active and Ready

### Rich Cafe Admin
- **Username**: `rich_cafe_admin`
- **Password**: `richadmin123`
- **Role**: Restaurant Administrator (Y Factory Restaurant only)
- **Restaurant**: Y Factory Restaurant
- **Status**: ✅ Active and Ready

## Kitchen Staff Account
- **Username**: `kitchen`
- **Password**: `kitchen123`
- **Role**: Kitchen Manager
- **Restaurant**: Flavour cafe | E.Fabrica
- **Position**: Head Chef

## Login URLs
- Super Admin Dashboard: `/superadmin/login`
- Restaurant Admin Dashboard: `/admin/login`
- Kitchen Dashboard: `/kitchen/login`

## Notes
- All accounts are active and approved
- Super admin accounts have access to all restaurants
- Restaurant admin and kitchen staff are restricted to their assigned restaurant
- Passwords are securely hashed using Werkzeug security functions

## Troubleshooting
If login issues persist:
1. Ensure you're using the correct login URL for your role
2. Check that cookies and sessions are enabled
3. Clear browser cache and try again
4. Verify the Flask server is running properly