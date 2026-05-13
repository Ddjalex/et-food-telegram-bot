const express = require('express');
const session = require('express-session');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const store = require('./store');

const app = express();

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use('/static', express.static(path.join(__dirname, '../static')));

app.use(session({
    secret: process.env.SESSION_SECRET || 'et-food-secret-key-2025',
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false, maxAge: 24 * 60 * 60 * 1000 }
}));

const upload = multer({
    dest: path.join(__dirname, '../static/uploads'),
    limits: { fileSize: 16 * 1024 * 1024 }
});

function checkAdminSession(req) {
    return req.session && req.session.admin_logged_in === true;
}

function requireAdmin(req, res, next) {
    if (!checkAdminSession(req)) return res.redirect('/admin/login');
    next();
}

function requireSuperAdmin(req, res, next) {
    if (!checkAdminSession(req)) return res.redirect('/superadmin/login');
    if (req.session.admin_role !== 'superadmin') return res.redirect('/superadmin/login');
    next();
}

function requireKitchen(req, res, next) {
    if (!req.session || !req.session.kitchen_logged_in) return res.redirect('/kitchen/login');
    next();
}

// ============================================================
// MAIN ROUTES
// ============================================================

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/webapp_beu_style.html'));
});

app.get('/webapp', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/webapp_beu_style.html'));
});

// ============================================================
// PUBLIC API ROUTES
// ============================================================

app.get('/api/restaurant-info', (req, res) => {
    try {
        const restaurants = store.findMany('restaurants', { is_active: true });
        if (!restaurants.length) {
            return res.json({ success: false, error: 'No restaurants available', company: { name: 'ET-FOOD', description: 'Food Delivery Service' }, restaurant: { name: 'Restaurant', description: 'Delicious Food' } });
        }
        const r = restaurants[0];
        res.json({
            success: true,
            company: { name: 'ET-FOOD', description: 'Food Delivery Service' },
            restaurant: { id: r.id, name: r.name, description: r.description, address: r.address, phone: r.phone, logo_url: r.logo_url, cover_image_url: r.cover_image_url, estimated_delivery_time: r.estimated_delivery_time }
        });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch restaurant information' });
    }
});

app.get('/api/restaurants', (req, res) => {
    try {
        const restaurants = store.findMany('restaurants', { is_active: true });
        const formatted = restaurants.map(r => ({
            id: r.id, name: r.name, description: r.description || '', address: r.address || '', phone: r.phone || '',
            logo_url: r.logo_url, cover_image_url: r.cover_image_url,
            estimated_delivery_time: r.estimated_delivery_time || '30-45 minutes',
            delivery_fee: r.delivery_fee || 0, minimum_order: r.minimum_order || 0,
            is_active: r.is_active !== false,
            menu_items_count: store.count('menu_items', { restaurant_id: r.id, available: true }),
            rating: r.rating || 4.5, is_featured: r.is_featured || false
        }));
        res.json({ success: true, restaurants: formatted, total: formatted.length });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch restaurants' });
    }
});

app.get('/api/menu', (req, res) => {
    try {
        let { restaurant_id, category } = req.query;
        if (!restaurant_id) {
            const rests = store.findMany('restaurants', { is_active: true });
            if (rests.length) restaurant_id = rests[0].id;
            else return res.status(404).json({ success: false, error: 'No restaurants available' });
        }
        const filter = { restaurant_id, available: true };
        if (category) filter.category = category;
        const items = store.findMany('menu_items', filter, 'category');
        res.json({ success: true, menu_items: items, restaurant_id });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch menu' });
    }
});

app.get('/api/categories', (req, res) => {
    try {
        const cats = store.findMany('categories', { is_active: true }, 'sort_order');
        res.json({ success: true, categories: cats });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch categories' });
    }
});

app.post('/api/orders', (req, res) => {
    try {
        const data = req.body;
        if (!data) return res.status(400).json({ success: false, error: 'No data provided' });
        for (const f of ['customer_name', 'customer_phone', 'items']) {
            if (!data[f]) return res.status(400).json({ success: false, error: `Missing required field: ${f}` });
        }
        let restaurant_id = data.restaurant_id;
        if (!restaurant_id) {
            const rests = store.findMany('restaurants', { is_active: true });
            if (rests.length) restaurant_id = rests[0].id;
            else return res.status(404).json({ success: false, error: 'No restaurants available' });
        }
        const order_id = store.insertOne('orders', {
            customer_name: data.customer_name,
            customer_phone: data.customer_phone,
            customer_address: data.customer_address,
            restaurant_id,
            telegram_user_id: data.telegram_user_id,
            items: data.items,
            total_amount: data.total_amount || 0,
            delivery_fee: data.delivery_fee || 0,
            status: 'pending',
            payment_method: data.payment_method || 'cash',
            payment_status: 'pending',
            location_lat: data.location_lat,
            location_lng: data.location_lng,
            special_instructions: data.special_instructions,
            order_number: `ET${Date.now()}`
        });
        const order = store.findById('orders', order_id);
        res.json({ success: true, order_id, order, message: 'Order created successfully' });
    } catch (e) {
        console.error('Error creating order:', e);
        res.status(500).json({ success: false, error: 'Failed to create order' });
    }
});

app.get('/api/orders', (req, res) => {
    try {
        const { restaurant_id, status, customer_id } = req.query;
        let filter = {};
        if (customer_id) filter.telegram_user_id = customer_id;
        else if (restaurant_id) { filter.restaurant_id = restaurant_id; if (status) filter.status = status; }
        else if (status) filter.status = status;
        const orders = store.findMany('orders', filter, 'created_at');
        res.json({ success: true, orders, total: orders.length });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch orders' });
    }
});

app.patch('/api/orders/:id', (req, res) => {
    try {
        const order = store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        store.updateById('orders', req.params.id, req.body);
        res.json({ success: true, order: store.findById('orders', req.params.id) });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to update order' });
    }
});

// ============================================================
// ADMIN ROUTES
// ============================================================

app.get(['/admin', '/admin/'], requireAdmin, (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/admin.html'));
});

app.get('/admin/login', (req, res) => {
    res.render('admin_login', { error: null });
});

app.post('/admin/login', (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) return res.render('admin_login', { error: 'Username and password are required' });
    const admin = store.findOne('admin_users', { username });
    if (admin && admin.password === password && (admin.role === 'admin' || admin.role === 'superadmin')) {
        req.session.admin_logged_in = true;
        req.session.admin_user_id = admin.id;
        req.session.admin_username = admin.username;
        req.session.admin_role = admin.role;
        store.updateById('admin_users', admin.id, { last_login: new Date() });
        return res.redirect('/admin');
    }
    res.render('admin_login', { error: 'Invalid username or password' });
});

app.get('/admin/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/admin/login');
});

app.get('/admin/dashboard', requireAdmin, (req, res) => {
    const admin = store.findById('admin_users', req.session.admin_user_id);
    let adminWithRestaurant = { ...admin };
    if (admin && admin.restaurant_id) {
        const restaurant = store.findById('restaurants', admin.restaurant_id);
        adminWithRestaurant.restaurant = restaurant;
    }
    res.render('restaurant_admin_dashboard', { admin: adminWithRestaurant });
});

// ============================================================
// SUPER ADMIN ROUTES
// ============================================================

app.get(['/superadmin', '/superadmin/'], requireSuperAdmin, (req, res) => {
    const admin = store.findById('admin_users', req.session.admin_user_id);
    const stats = {
        total_orders: store.count('orders'),
        total_restaurants: store.count('restaurants'),
        total_drivers: store.count('drivers'),
        total_admins: store.count('admin_users')
    };
    res.render('super_admin_dashboard', { stats, admin: admin || { username: 'superadmin', full_name: 'Super Administrator' } });
});

app.get('/superadmin/login', (req, res) => {
    res.render('superadmin_login', { error: null });
});

app.post('/superadmin/login', (req, res) => {
    const data = req.is('json') ? req.body : req.body;
    const { username, password } = data;
    if (!username || !password) {
        if (req.is('json')) return res.status(400).json({ success: false, message: 'Username and password are required' });
        return res.render('superadmin_login', { error: 'Username and password are required' });
    }
    const admin = store.findOne('admin_users', { username });
    if (admin && admin.password === password && admin.role === 'superadmin') {
        req.session.admin_logged_in = true;
        req.session.admin_user_id = admin.id;
        req.session.admin_username = admin.username;
        req.session.admin_role = 'superadmin';
        store.updateById('admin_users', admin.id, { last_login: new Date() });
        if (req.is('json')) return res.json({ success: true, redirect: '/superadmin' });
        return res.redirect('/superadmin');
    }
    if (req.is('json')) return res.status(401).json({ success: false, message: 'Invalid credentials or insufficient privileges' });
    res.render('superadmin_login', { error: 'Invalid credentials or insufficient privileges' });
});

// ============================================================
// SUPER ADMIN API ROUTES
// ============================================================

app.get('/api/restaurants/super-admin', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const restaurants = store.findMany('restaurants');
        const formatted = restaurants.map(r => ({
            id: r.id, name: r.name, description: r.description, address: r.address, phone: r.phone,
            logo_url: r.logo_url, cover_image_url: r.cover_image_url,
            estimated_delivery_time: r.estimated_delivery_time,
            is_active: r.is_active !== false,
            created_at: r.created_at,
            menu_items_count: store.count('menu_items', { restaurant_id: r.id }),
            total_menu_items: store.count('menu_items', { restaurant_id: r.id }),
            orders_today: store.count('orders', { restaurant_id: r.id }),
            total_orders: store.count('orders', { restaurant_id: r.id }),
            delivery_fee: r.delivery_fee || 0, minimum_order: r.minimum_order || 0
        }));
        res.json({ success: true, restaurants: formatted, total_restaurants: formatted.length });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch restaurants' });
    }
});

app.post('/api/restaurants/super-admin', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const data = req.body;
        for (const f of ['name', 'address', 'phone']) {
            if (!data[f]) return res.status(400).json({ success: false, message: `${f} is required` });
        }
        if (store.findOne('restaurants', { name: data.name })) return res.status(400).json({ success: false, message: 'Restaurant name already exists' });
        const id = store.insertOne('restaurants', {
            name: data.name, address: data.address, phone: data.phone,
            description: data.description || '',
            estimated_delivery_time: data.estimated_delivery_time || '30-45 minutes',
            delivery_fee: parseFloat(data.delivery_fee) || 0,
            minimum_order: parseFloat(data.minimum_order) || 0,
            is_active: data.is_active !== false,
            is_featured: data.is_featured || false,
            logo_url: data.logo_url || null, cover_image_url: data.cover_image_url || null
        });
        res.json({ success: true, message: `Restaurant ${data.name} created successfully`, restaurant_id: id });
    } catch (e) {
        res.status(500).json({ success: false, message: 'Failed to create restaurant' });
    }
});

app.put('/api/restaurants/super-admin/:id', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const r = store.findById('restaurants', req.params.id);
        if (!r) return res.status(404).json({ success: false, error: 'Restaurant not found' });
        store.updateById('restaurants', req.params.id, req.body);
        res.json({ success: true, message: 'Restaurant updated successfully' });
    } catch (e) {
        res.status(500).json({ success: false, message: 'Failed to update restaurant' });
    }
});

app.delete('/api/restaurants/super-admin/:id', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    store.deleteOne('restaurants', { id: req.params.id });
    res.json({ success: true, message: 'Restaurant deleted successfully' });
});

app.get('/api/super-admin/admins', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const admins = store.findMany('admin_users');
        const formatted = admins.map(a => ({
            id: a.id, username: a.username, role: a.role || 'admin',
            restaurant_id: a.restaurant_id, restaurant_name: a.restaurant_id ? (store.findById('restaurants', a.restaurant_id) || {}).name || 'N/A' : 'N/A',
            is_active: a.is_active !== false, last_login: a.last_login || 'Never', created_at: a.created_at
        }));
        res.json({ success: true, admins: formatted });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch admins' });
    }
});

app.post('/api/super-admin/admins', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const data = req.body;
        for (const f of ['username', 'password', 'full_name']) {
            if (!data[f]) return res.status(400).json({ success: false, message: `${f} is required` });
        }
        if (store.findOne('admin_users', { username: data.username })) return res.status(400).json({ success: false, message: 'Username already exists' });
        const id = store.insertOne('admin_users', {
            username: data.username, password: data.password,
            full_name: data.full_name, email: data.email || '',
            role: data.role || 'admin', restaurant_id: data.restaurant_id || null, is_active: true
        });
        res.json({ success: true, message: `Admin ${data.username} created successfully`, admin_id: id });
    } catch (e) {
        res.status(500).json({ success: false, message: 'Failed to create admin' });
    }
});

app.get('/api/super-admin/drivers', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const drivers = store.findMany('drivers');
        const formatted = drivers.map(d => ({
            id: d.id, name: d.name, phone: d.phone || d.phone_number,
            vehicle_type: d.vehicle_type || 'Unknown',
            is_approved: d.is_approved || false, is_active: d.is_active !== false,
            location_lat: d.current_lat, location_lng: d.current_lng,
            last_location_update: d.last_location_update || 'Never', created_at: d.created_at
        }));
        res.json({ success: true, drivers: formatted });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch drivers' });
    }
});

app.get('/api/super-admin/stats', (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        res.json({
            success: true,
            stats: {
                total_restaurants: store.count('restaurants'),
                total_menu_items: store.count('menu_items'),
                total_orders: store.count('orders'),
                total_drivers: store.count('drivers'),
                total_admins: store.count('admin_users'),
                pending_drivers: store.count('drivers', { is_approved: false }),
                active_drivers: store.count('drivers', { is_active: true, is_approved: true }),
                orders_today: store.count('orders'),
                revenue_today: 0
            }
        });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch statistics' });
    }
});

// ============================================================
// MENU MANAGEMENT API (Admin)
// ============================================================

app.get('/api/admin/menu', (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const { restaurant_id } = req.query;
        const filter = restaurant_id ? { restaurant_id } : {};
        const items = store.findMany('menu_items', filter);
        res.json({ success: true, menu_items: items });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch menu items' });
    }
});

app.post('/api/admin/menu', (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const data = req.body;
        if (!data.name || !data.price || !data.restaurant_id) return res.status(400).json({ success: false, error: 'name, price, restaurant_id are required' });
        const id = store.insertOne('menu_items', {
            name: data.name, price: parseFloat(data.price), restaurant_id: data.restaurant_id,
            description: data.description || '', image_url: data.image_url || null,
            category: data.category || 'main', available: data.available !== false,
            preparation_time: parseInt(data.preparation_time) || 15
        });
        res.json({ success: true, message: 'Menu item created', item_id: id });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to create menu item' });
    }
});

app.put('/api/admin/menu/:id', (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const item = store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Menu item not found' });
        store.updateById('menu_items', req.params.id, req.body);
        res.json({ success: true, message: 'Menu item updated' });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to update menu item' });
    }
});

app.delete('/api/admin/menu/:id', (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    store.deleteOne('menu_items', { id: req.params.id });
    res.json({ success: true, message: 'Menu item deleted' });
});

// ============================================================
// KITCHEN ROUTES
// ============================================================

app.get('/kitchen/login', (req, res) => {
    res.render('kitchen_login', { message: null });
});

app.post('/kitchen/login', (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) return res.render('kitchen_login', { message: 'Username and password are required' });
    const user = store.findOne('admin_users', { username });
    if (user && user.password === password && (user.role === 'kitchen' || user.role === 'admin' || user.role === 'superadmin')) {
        req.session.kitchen_logged_in = true;
        req.session.kitchen_user_id = user.id;
        req.session.kitchen_username = user.username;
        req.session.kitchen_restaurant_id = user.restaurant_id;
        return res.redirect('/kitchen/dashboard');
    }
    res.render('kitchen_login', { message: 'Invalid username or password' });
});

app.get('/kitchen/logout', (req, res) => {
    req.session.kitchen_logged_in = false;
    res.redirect('/kitchen/login');
});

app.get(['/kitchen', '/kitchen/'], requireKitchen, (req, res) => {
    res.redirect('/kitchen/dashboard');
});

app.get('/kitchen/dashboard', requireKitchen, (req, res) => {
    const restaurant = req.session.kitchen_restaurant_id
        ? store.findById('restaurants', req.session.kitchen_restaurant_id)
        : null;
    res.render('kitchen_dashboard', { restaurant });
});

app.get('/kitchen/food-management', requireKitchen, (req, res) => {
    const restaurant = req.session.kitchen_restaurant_id
        ? store.findById('restaurants', req.session.kitchen_restaurant_id)
        : null;
    res.render('kitchen_food_management', { restaurant });
});

// Kitchen API
app.get('/api/kitchen/orders', requireKitchen, (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const filter = {};
        if (restaurant_id) filter.restaurant_id = restaurant_id;
        const orders = store.findMany('orders', filter, 'created_at');
        res.json({ success: true, orders });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch orders' });
    }
});

app.patch('/api/kitchen/orders/:id', requireKitchen, (req, res) => {
    try {
        const order = store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        store.updateById('orders', req.params.id, req.body);
        res.json({ success: true, order: store.findById('orders', req.params.id) });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to update order' });
    }
});

app.get('/api/kitchen/menu-items', requireKitchen, (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const filter = restaurant_id ? { restaurant_id } : {};
        const items = store.findMany('menu_items', filter);
        res.json({ success: true, menu_items: items });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch menu items' });
    }
});

app.patch('/api/kitchen/menu-items/:id/availability', requireKitchen, (req, res) => {
    try {
        const item = store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Item not found' });
        store.updateById('menu_items', req.params.id, { available: req.body.available });
        res.json({ success: true });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to update availability' });
    }
});

// ============================================================
// DRIVER ROUTES
// ============================================================

app.get('/driver-panel', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/enhanced_driver_panel.html'));
});

app.post('/api/driver/location', (req, res) => {
    try {
        const { driver_id, lat, lng } = req.body;
        if (!driver_id) return res.status(400).json({ success: false, error: 'driver_id required' });
        store.updateById('drivers', driver_id, { current_lat: lat, current_lng: lng, last_location_update: new Date() });
        res.json({ success: true });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to update location' });
    }
});

app.post('/api/driver/register', (req, res) => {
    try {
        const data = req.body;
        if (!data.name || !data.phone_number) return res.status(400).json({ success: false, error: 'name and phone_number are required' });
        const id = store.insertOne('drivers', {
            name: data.name, phone_number: data.phone_number,
            telegram_user_id: data.telegram_user_id,
            vehicle_type: data.vehicle_type || 'motorcycle',
            license_number: data.license_number,
            is_active: true, is_available: false, is_approved: false,
            rating: 5.0, total_deliveries: 0
        });
        res.json({ success: true, driver_id: id });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to register driver' });
    }
});

// ============================================================
// FILE UPLOAD
// ============================================================

app.post('/api/upload', upload.single('file'), (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    if (!req.file) return res.status(400).json({ success: false, error: 'No file uploaded' });
    const filename = `${Date.now()}_${req.file.originalname}`;
    const destPath = path.join(__dirname, '../static/uploads', filename);
    fs.renameSync(req.file.path, destPath);
    res.json({ success: true, url: `/static/uploads/${filename}`, filename });
});

// ============================================================
// CHANGE PASSWORD
// ============================================================

app.get('/admin/change-password', requireAdmin, (req, res) => {
    res.render('change_password', { error: null, success: null });
});

app.post('/admin/change-password', requireAdmin, (req, res) => {
    const { current_password, new_password, confirm_password } = req.body;
    const admin = store.findById('admin_users', req.session.admin_user_id);
    if (!admin) return res.render('change_password', { error: 'Admin not found', success: null });
    if (admin.password !== current_password) return res.render('change_password', { error: 'Current password is incorrect', success: null });
    if (new_password !== confirm_password) return res.render('change_password', { error: 'Passwords do not match', success: null });
    if (new_password.length < 8) return res.render('change_password', { error: 'Password must be at least 8 characters', success: null });
    store.updateById('admin_users', admin.id, { password: new_password });
    res.render('change_password', { error: null, success: 'Password changed successfully' });
});

// ============================================================
// ERROR HANDLERS
// ============================================================

app.use((req, res) => {
    res.status(404).json({ success: false, error: 'Endpoint not found' });
});

app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).json({ success: false, error: 'Internal server error' });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`ET-FOOD Node.js server running on port ${PORT}`);
    console.log(`Restaurants: ${store.count('restaurants')}`);
    console.log(`Menu Items: ${store.count('menu_items')}`);
    console.log(`Categories: ${store.count('categories')}`);
    console.log(`Admin Users: ${store.count('admin_users')}`);
});

module.exports = app;
