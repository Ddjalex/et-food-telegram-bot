require('dotenv').config({ path: require('path').join(__dirname, '../.env.example') });

const express = require('express');
const session = require('express-session');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const store = require('./store');
const { runMigration } = require('./migrate');

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

app.get('/api/restaurant-info', async (req, res) => {
    try {
        const restaurants = await store.findMany('restaurants', { is_active: true });
        if (!restaurants.length) {
            return res.json({ success: false, error: 'No restaurants available', company: { name: 'ET-FOOD' }, restaurant: { name: 'Restaurant' } });
        }
        const r = restaurants[0];
        res.json({
            success: true,
            company: { name: 'ET-FOOD', description: 'Food Delivery Service' },
            restaurant: { id: r.id, name: r.name, description: r.description, address: r.address, phone: r.phone, logo_url: r.logo_url, cover_image_url: r.cover_image_url, estimated_delivery_time: r.estimated_delivery_time }
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch restaurant information' });
    }
});

app.get('/api/restaurants', async (req, res) => {
    try {
        const restaurants = await store.findMany('restaurants', { is_active: true });
        const formatted = await Promise.all(restaurants.map(async r => ({
            id: r.id, name: r.name, description: r.description || '', address: r.address || '', phone: r.phone || '',
            logo_url: r.logo_url, cover_image_url: r.cover_image_url,
            estimated_delivery_time: r.estimated_delivery_time || '30-45 minutes',
            delivery_fee: parseFloat(r.delivery_fee) || 0, minimum_order: parseFloat(r.minimum_order) || 0,
            is_active: r.is_active !== false,
            menu_items_count: await store.count('menu_items', { restaurant_id: r.id, available: true }),
            rating: parseFloat(r.rating) || 4.5, is_featured: r.is_featured || false
        })));
        res.json({ success: true, restaurants: formatted, total: formatted.length });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch restaurants' });
    }
});

app.get('/api/menu', async (req, res) => {
    try {
        let { restaurant_id, category } = req.query;
        if (!restaurant_id) {
            const rests = await store.findMany('restaurants', { is_active: true });
            if (rests.length) restaurant_id = rests[0].id;
            else return res.status(404).json({ success: false, error: 'No restaurants available' });
        }
        const filter = { restaurant_id, available: true };
        if (category) filter.category = category;
        const items = await store.findMany('menu_items', filter, 'category');
        res.json({ success: true, menu_items: items, restaurant_id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch menu' });
    }
});

app.get('/api/categories', async (req, res) => {
    try {
        const cats = await store.findMany('categories', { is_active: true }, 'sort_order');
        res.json({ success: true, categories: cats });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch categories' });
    }
});

app.post('/api/orders', async (req, res) => {
    try {
        const data = req.body;
        if (!data) return res.status(400).json({ success: false, error: 'No data provided' });
        for (const f of ['customer_name', 'customer_phone', 'items']) {
            if (!data[f]) return res.status(400).json({ success: false, error: `Missing required field: ${f}` });
        }
        let restaurant_id = data.restaurant_id;
        if (!restaurant_id) {
            const rests = await store.findMany('restaurants', { is_active: true });
            if (rests.length) restaurant_id = rests[0].id;
            else return res.status(404).json({ success: false, error: 'No restaurants available' });
        }
        const order_id = await store.insertOne('orders', {
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
        const order = await store.findById('orders', order_id);
        res.json({ success: true, order_id, order, message: 'Order created successfully' });
    } catch (e) {
        console.error('Error creating order:', e);
        res.status(500).json({ success: false, error: 'Failed to create order' });
    }
});

app.get('/api/orders', async (req, res) => {
    try {
        const { restaurant_id, status, customer_id } = req.query;
        let filter = {};
        if (customer_id) filter.telegram_user_id = customer_id;
        else if (restaurant_id) { filter.restaurant_id = restaurant_id; if (status) filter.status = status; }
        else if (status) filter.status = status;
        const orders = await store.findMany('orders', filter, 'created_at');
        res.json({ success: true, orders, total: orders.length });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch orders' });
    }
});

app.patch('/api/orders/:id', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        await store.updateById('orders', req.params.id, req.body);
        res.json({ success: true, order: await store.findById('orders', req.params.id) });
    } catch (e) {
        console.error(e);
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

app.post('/admin/login', async (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) return res.render('admin_login', { error: 'Username and password are required' });
    try {
        const admin = await store.findOne('admin_users', { username });
        if (admin && admin.password === password && (admin.role === 'admin' || admin.role === 'superadmin')) {
            req.session.admin_logged_in = true;
            req.session.admin_user_id = admin.id;
            req.session.admin_username = admin.username;
            req.session.admin_role = admin.role;
            await store.updateById('admin_users', admin.id, { last_login: new Date() });
            return res.redirect('/admin');
        }
        res.render('admin_login', { error: 'Invalid username or password' });
    } catch (e) {
        console.error(e);
        res.render('admin_login', { error: 'Login failed, please try again' });
    }
});

app.get('/admin/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/admin/login');
});

app.get('/admin/dashboard', requireAdmin, async (req, res) => {
    try {
        const admin = await store.findById('admin_users', req.session.admin_user_id);
        let adminWithRestaurant = { ...admin };
        if (admin && admin.restaurant_id) {
            adminWithRestaurant.restaurant = await store.findById('restaurants', admin.restaurant_id);
        }
        res.render('restaurant_admin_dashboard', { admin: adminWithRestaurant });
    } catch (e) {
        console.error(e);
        res.render('restaurant_admin_dashboard', { admin: { username: req.session.admin_username } });
    }
});

// ============================================================
// SUPER ADMIN ROUTES
// ============================================================

app.get(['/superadmin', '/superadmin/'], requireSuperAdmin, async (req, res) => {
    try {
        const admin = await store.findById('admin_users', req.session.admin_user_id);
        const stats = {
            total_orders: await store.count('orders'),
            total_restaurants: await store.count('restaurants'),
            total_drivers: await store.count('drivers'),
            total_admins: await store.count('admin_users')
        };
        res.render('super_admin_dashboard', { stats, admin: admin || { username: 'superadmin', full_name: 'Super Administrator' } });
    } catch (e) {
        console.error(e);
        res.render('super_admin_dashboard', { stats: {}, admin: { username: 'superadmin', full_name: 'Super Administrator' } });
    }
});

app.get('/superadmin/login', (req, res) => {
    res.render('superadmin_login', { error: null });
});

app.post('/superadmin/login', async (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) {
        if (req.is('json')) return res.status(400).json({ success: false, message: 'Username and password are required' });
        return res.render('superadmin_login', { error: 'Username and password are required' });
    }
    try {
        const admin = await store.findOne('admin_users', { username });
        if (admin && admin.password === password && admin.role === 'superadmin') {
            req.session.admin_logged_in = true;
            req.session.admin_user_id = admin.id;
            req.session.admin_username = admin.username;
            req.session.admin_role = 'superadmin';
            await store.updateById('admin_users', admin.id, { last_login: new Date() });
            if (req.is('json')) return res.json({ success: true, redirect: '/superadmin' });
            return res.redirect('/superadmin');
        }
        if (req.is('json')) return res.status(401).json({ success: false, message: 'Invalid credentials or insufficient privileges' });
        res.render('superadmin_login', { error: 'Invalid credentials or insufficient privileges' });
    } catch (e) {
        console.error(e);
        if (req.is('json')) return res.status(500).json({ success: false, message: 'Login failed' });
        res.render('superadmin_login', { error: 'Login failed, please try again' });
    }
});

// ============================================================
// SUPER ADMIN API ROUTES
// ============================================================

app.get('/api/restaurants/super-admin', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const restaurants = await store.findMany('restaurants');
        const formatted = await Promise.all(restaurants.map(async r => ({
            id: r.id, name: r.name, description: r.description, address: r.address, phone: r.phone,
            logo_url: r.logo_url, cover_image_url: r.cover_image_url,
            estimated_delivery_time: r.estimated_delivery_time,
            is_active: r.is_active !== false,
            created_at: r.created_at,
            menu_items_count: await store.count('menu_items', { restaurant_id: r.id }),
            total_menu_items: await store.count('menu_items', { restaurant_id: r.id }),
            orders_today: await store.count('orders', { restaurant_id: r.id }),
            total_orders: await store.count('orders', { restaurant_id: r.id }),
            delivery_fee: parseFloat(r.delivery_fee) || 0,
            minimum_order: parseFloat(r.minimum_order) || 0
        })));
        res.json({ success: true, restaurants: formatted, total_restaurants: formatted.length });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch restaurants' });
    }
});

app.post('/api/restaurants/super-admin', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const data = req.body;
        for (const f of ['name', 'address', 'phone']) {
            if (!data[f]) return res.status(400).json({ success: false, message: `${f} is required` });
        }
        if (await store.findOne('restaurants', { name: data.name })) return res.status(400).json({ success: false, message: 'Restaurant name already exists' });
        const id = await store.insertOne('restaurants', {
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
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to create restaurant' });
    }
});

app.put('/api/restaurants/super-admin/:id', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const r = await store.findById('restaurants', req.params.id);
        if (!r) return res.status(404).json({ success: false, error: 'Restaurant not found' });
        await store.updateById('restaurants', req.params.id, req.body);
        res.json({ success: true, message: 'Restaurant updated successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to update restaurant' });
    }
});

app.delete('/api/restaurants/super-admin/:id', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        await store.deleteOne('restaurants', { id: req.params.id });
        res.json({ success: true, message: 'Restaurant deleted successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to delete restaurant' });
    }
});

app.get('/api/super-admin/admins', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const admins = await store.findMany('admin_users');
        const formatted = await Promise.all(admins.map(async a => {
            let restaurant_name = 'N/A';
            if (a.restaurant_id) {
                const r = await store.findById('restaurants', a.restaurant_id);
                if (r) restaurant_name = r.name;
            }
            return {
                id: a.id, username: a.username, role: a.role || 'admin',
                restaurant_id: a.restaurant_id, restaurant_name,
                is_active: a.is_active !== false, last_login: a.last_login || 'Never', created_at: a.created_at
            };
        }));
        res.json({ success: true, admins: formatted });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch admins' });
    }
});

app.post('/api/super-admin/admins', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const data = req.body;
        for (const f of ['username', 'password', 'full_name']) {
            if (!data[f]) return res.status(400).json({ success: false, message: `${f} is required` });
        }
        if (await store.findOne('admin_users', { username: data.username })) return res.status(400).json({ success: false, message: 'Username already exists' });
        const id = await store.insertOne('admin_users', {
            username: data.username, password: data.password,
            full_name: data.full_name, email: data.email || '',
            role: data.role || 'admin', restaurant_id: data.restaurant_id || null, is_active: true
        });
        res.json({ success: true, message: `Admin ${data.username} created successfully`, admin_id: id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to create admin' });
    }
});

app.get('/api/super-admin/drivers', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const drivers = await store.findMany('drivers');
        const formatted = drivers.map(d => ({
            id: d.id, name: d.name, phone: d.phone || d.phone_number,
            phone_number: d.phone_number || d.phone,
            vehicle_type: d.vehicle_type || 'Unknown',
            is_approved: d.is_approved || false, is_active: d.is_active !== false,
            is_available: d.is_available || false,
            current_lat: d.current_lat, current_lng: d.current_lng,
            last_location_update: d.last_location_update || null, created_at: d.created_at
        }));
        res.json({ success: true, drivers: formatted });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch drivers' });
    }
});

app.get('/api/super-admin/drivers/pending', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const drivers = await store.findMany('drivers', { is_approved: false });
        const formatted = drivers.map(d => ({
            id: d.id, name: d.name, phone_number: d.phone_number || d.phone,
            vehicle_type: d.vehicle_type || 'Unknown',
            is_active: d.is_active !== false, created_at: d.created_at
        }));
        res.json({ success: true, drivers: formatted });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch pending drivers' });
    }
});

app.get('/api/super-admin/drivers/approved', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const drivers = await store.findMany('drivers', { is_approved: true });
        const formatted = drivers.map(d => ({
            id: d.id, name: d.name, phone_number: d.phone_number || d.phone,
            vehicle_type: d.vehicle_type || 'Unknown',
            is_active: d.is_active !== false, is_available: d.is_available || false,
            current_lat: d.current_lat, current_lng: d.current_lng,
            last_location_update: d.last_location_update || null, created_at: d.created_at,
            total_deliveries: d.total_deliveries || 0, rating: d.rating || 5.0
        }));
        res.json({ success: true, drivers: formatted });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch approved drivers' });
    }
});

app.get('/api/super-admin/drivers/stats', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const [total, approved, pending, active] = await Promise.all([
            store.count('drivers'),
            store.count('drivers', { is_approved: true }),
            store.count('drivers', { is_approved: false }),
            store.count('drivers', { is_active: true, is_approved: true })
        ]);
        res.json({ success: true, stats: { total, approved, pending, active } });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch driver stats' });
    }
});

app.post('/api/super-admin/drivers/:id/approve', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const driver = await store.findById('drivers', req.params.id);
        if (!driver) return res.status(404).json({ success: false, message: 'Driver not found' });
        await store.updateById('drivers', req.params.id, { is_approved: true, is_active: true });
        res.json({ success: true, message: 'Driver approved successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to approve driver' });
    }
});

app.post('/api/super-admin/drivers/:id/reject', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const driver = await store.findById('drivers', req.params.id);
        if (!driver) return res.status(404).json({ success: false, message: 'Driver not found' });
        await store.updateById('drivers', req.params.id, { is_approved: false, is_active: false, rejection_reason: req.body.reason || 'Rejected by admin' });
        res.json({ success: true, message: 'Driver rejected successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to reject driver' });
    }
});

app.delete('/api/super-admin/drivers/:id', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const driver = await store.findById('drivers', req.params.id);
        if (!driver) return res.status(404).json({ success: false, message: 'Driver not found' });
        await store.deleteOne('drivers', { id: req.params.id });
        res.json({ success: true, message: 'Driver deleted successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to delete driver' });
    }
});

app.get('/api/super-admin/drivers/:id/documents', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const driver = await store.findById('drivers', req.params.id);
        if (!driver) return res.status(404).json({ success: false, message: 'Driver not found' });
        res.json({
            success: true,
            driver_info: { id: driver.id, name: driver.name, phone: driver.phone_number, vehicle_type: driver.vehicle_type },
            documents: []
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to fetch driver documents' });
    }
});

app.post('/api/super-admin/drivers/:id/request-location', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const driver = await store.findById('drivers', req.params.id);
        if (!driver) return res.status(404).json({ success: false, message: 'Driver not found' });
        res.json({ success: true, message: `Location request sent to ${driver.name}` });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to request location' });
    }
});

app.get('/api/dashboard-stats', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const [totalAdmins, totalRestaurants, totalOrders, totalRevenue] = await Promise.all([
            store.count('admin_users'),
            store.count('restaurants', { is_active: true }),
            store.count('orders'),
            store.findMany('orders', {}, 'created_at')
        ]);
        const revenue = totalRevenue.reduce((sum, o) => sum + parseFloat(o.total_amount || 0), 0);
        res.json({ success: true, totalAdmins, totalRestaurants, todayOrders: totalOrders, totalRevenue: revenue });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch dashboard stats' });
    }
});

app.get('/api/overview-data', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const orders = await store.findMany('orders', {}, 'created_at');
        const statusData = {};
        const revenueByDate = {};
        for (const o of orders) {
            statusData[o.status] = (statusData[o.status] || 0) + 1;
            const date = new Date(o.created_at).toLocaleDateString();
            revenueByDate[date] = (revenueByDate[date] || 0) + parseFloat(o.total_amount || 0);
        }
        const revenueData = Object.entries(revenueByDate).slice(-7).map(([date, amount]) => ({ date, amount }));
        res.json({ success: true, status_data: statusData, revenue_data: revenueData });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch overview data' });
    }
});

app.get('/api/super-admin/stats', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const [total_restaurants, total_menu_items, total_orders, total_drivers, total_admins, pending_drivers, active_drivers] = await Promise.all([
            store.count('restaurants'),
            store.count('menu_items'),
            store.count('orders'),
            store.count('drivers'),
            store.count('admin_users'),
            store.count('drivers', { is_approved: false }),
            store.count('drivers', { is_active: true, is_approved: true })
        ]);
        res.json({ success: true, stats: { total_restaurants, total_menu_items, total_orders, total_drivers, total_admins, pending_drivers, active_drivers, orders_today: total_orders, revenue_today: 0 } });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch statistics' });
    }
});

// ============================================================
// MENU MANAGEMENT API (Admin)
// ============================================================

app.get('/api/admin/menu', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const { restaurant_id } = req.query;
        const filter = restaurant_id ? { restaurant_id } : {};
        const items = await store.findMany('menu_items', filter);
        res.json({ success: true, menu_items: items });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch menu items' });
    }
});

app.post('/api/admin/menu', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const data = req.body;
        if (!data.name || !data.price || !data.restaurant_id) return res.status(400).json({ success: false, error: 'name, price, restaurant_id are required' });
        const id = await store.insertOne('menu_items', {
            name: data.name, price: parseFloat(data.price), restaurant_id: data.restaurant_id,
            description: data.description || '', image_url: data.image_url || null,
            category: data.category || 'main', available: data.available !== false,
            preparation_time: parseInt(data.preparation_time) || 15
        });
        res.json({ success: true, message: 'Menu item created', item_id: id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to create menu item' });
    }
});

app.put('/api/admin/menu/:id', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const item = await store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Menu item not found' });
        await store.updateById('menu_items', req.params.id, req.body);
        res.json({ success: true, message: 'Menu item updated' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update menu item' });
    }
});

app.delete('/api/admin/menu/:id', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        await store.deleteOne('menu_items', { id: req.params.id });
        res.json({ success: true, message: 'Menu item deleted' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to delete menu item' });
    }
});

// ============================================================
// KITCHEN ROUTES
// ============================================================

app.get('/kitchen/login', (req, res) => {
    res.render('kitchen_login', { message: null });
});

app.post('/kitchen/login', async (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) return res.render('kitchen_login', { message: 'Username and password are required' });
    try {
        const user = await store.findOne('admin_users', { username });
        if (user && user.password === password && (user.role === 'kitchen' || user.role === 'admin' || user.role === 'superadmin')) {
            req.session.kitchen_logged_in = true;
            req.session.kitchen_user_id = user.id;
            req.session.kitchen_username = user.username;
            req.session.kitchen_restaurant_id = user.restaurant_id;
            return res.redirect('/kitchen/dashboard');
        }
        res.render('kitchen_login', { message: 'Invalid username or password' });
    } catch (e) {
        console.error(e);
        res.render('kitchen_login', { message: 'Login failed, please try again' });
    }
});

app.get('/kitchen/logout', (req, res) => {
    req.session.kitchen_logged_in = false;
    res.redirect('/kitchen/login');
});

app.get(['/kitchen', '/kitchen/'], requireKitchen, (req, res) => {
    res.redirect('/kitchen/dashboard');
});

app.get('/kitchen/dashboard', requireKitchen, async (req, res) => {
    try {
        const restaurant = req.session.kitchen_restaurant_id
            ? await store.findById('restaurants', req.session.kitchen_restaurant_id)
            : null;
        res.render('kitchen_dashboard', { restaurant });
    } catch (e) {
        res.render('kitchen_dashboard', { restaurant: null });
    }
});

app.get('/kitchen/food-management', requireKitchen, async (req, res) => {
    try {
        const restaurant = req.session.kitchen_restaurant_id
            ? await store.findById('restaurants', req.session.kitchen_restaurant_id)
            : null;
        res.render('kitchen_food_management', { restaurant });
    } catch (e) {
        res.render('kitchen_food_management', { restaurant: null });
    }
});

// Kitchen API
app.get('/api/kitchen/orders', requireKitchen, async (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const filter = restaurant_id ? { restaurant_id } : {};
        const orders = await store.findMany('orders', filter, 'created_at');
        res.json({ success: true, orders });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch orders' });
    }
});

app.patch('/api/kitchen/orders/:id', requireKitchen, async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        await store.updateById('orders', req.params.id, req.body);
        res.json({ success: true, order: await store.findById('orders', req.params.id) });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update order' });
    }
});

app.get('/api/kitchen/menu-items', requireKitchen, async (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const filter = restaurant_id ? { restaurant_id } : {};
        const items = await store.findMany('menu_items', filter);
        res.json({ success: true, menu_items: items });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch menu items' });
    }
});

app.patch('/api/kitchen/menu-items/:id/availability', requireKitchen, async (req, res) => {
    try {
        const item = await store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Item not found' });
        await store.updateById('menu_items', req.params.id, { available: req.body.available });
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update availability' });
    }
});

// ============================================================
// DRIVER ROUTES
// ============================================================

app.get('/driver-panel', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/enhanced_driver_panel.html'));
});

app.post('/api/driver/location', async (req, res) => {
    try {
        const { driver_id, lat, lng } = req.body;
        if (!driver_id) return res.status(400).json({ success: false, error: 'driver_id required' });
        await store.updateById('drivers', driver_id, { current_lat: lat, current_lng: lng, last_location_update: new Date() });
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update location' });
    }
});

app.post('/api/driver/register', async (req, res) => {
    try {
        const data = req.body;
        if (!data.name || !data.phone_number) return res.status(400).json({ success: false, error: 'name and phone_number are required' });
        const id = await store.insertOne('drivers', {
            name: data.name, phone_number: data.phone_number,
            telegram_user_id: data.telegram_user_id,
            vehicle_type: data.vehicle_type || 'motorcycle',
            license_number: data.license_number,
            is_active: true, is_available: false, is_approved: false,
            rating: 5.0, total_deliveries: 0
        });
        res.json({ success: true, driver_id: id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to register driver' });
    }
});

// ============================================================
// DRIVERS API (used by admin.html)
// ============================================================

app.get('/api/drivers', async (req, res) => {
    try {
        const drivers = await store.findMany('drivers');
        const formatted = drivers.map(d => ({
            ...d,
            approval_status: d.is_approved ? 'approved' : (d.rejection_reason ? 'rejected' : 'pending')
        }));
        res.json(formatted);
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch drivers' });
    }
});

app.post('/api/drivers', async (req, res) => {
    try {
        const data = req.body;
        if (!data.name || !data.phone_number) return res.status(400).json({ success: false, error: 'name and phone_number required' });
        const id = await store.insertOne('drivers', {
            name: data.name, phone_number: data.phone_number,
            telegram_user_id: data.telegram_user_id || null,
            vehicle_type: data.vehicle_type || 'motorcycle',
            is_active: true, is_available: false, is_approved: false,
            rating: 5.0, total_deliveries: 0
        });
        res.json({ success: true, driver_id: id, message: 'Driver added' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to add driver' });
    }
});

app.post('/api/drivers/:id/approve', async (req, res) => {
    try {
        const driver = await store.findById('drivers', req.params.id);
        if (!driver) return res.status(404).json({ success: false, message: 'Driver not found' });
        await store.updateById('drivers', req.params.id, { is_approved: true, is_active: true });
        res.json({ success: true, message: 'Driver approved successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to approve driver' });
    }
});

app.post('/api/drivers/:id/reject', async (req, res) => {
    try {
        const driver = await store.findById('drivers', req.params.id);
        if (!driver) return res.status(404).json({ success: false, message: 'Driver not found' });
        await store.updateById('drivers', req.params.id, { is_approved: false, is_active: false, rejection_reason: req.body.reason || 'Rejected' });
        res.json({ success: true, message: 'Driver rejected' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to reject driver' });
    }
});

app.put('/api/drivers/:id/availability', async (req, res) => {
    try {
        await store.updateById('drivers', req.params.id, { is_available: req.body.is_available });
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update availability' });
    }
});

// ============================================================
// ORDERS API — additional endpoints for admin.html
// ============================================================

app.get('/api/orders/:id', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        res.json(order);
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch order' });
    }
});

app.put('/api/orders/:id/status', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        await store.updateById('orders', req.params.id, { status: req.body.status });
        res.json({ success: true, order: await store.findById('orders', req.params.id) });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update order status' });
    }
});

// ============================================================
// MENU API — direct /api/menu/:id and /api/menu POST/PUT/DELETE for admin.html
// ============================================================

app.get('/api/menu/:id', async (req, res) => {
    try {
        const item = await store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Menu item not found' });
        res.json(item);
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch menu item' });
    }
});

app.post('/api/menu', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const data = req.body;
        if (!data.name || !data.price) return res.status(400).json({ success: false, error: 'name and price are required' });
        let restaurant_id = data.restaurant_id;
        if (!restaurant_id) {
            const rests = await store.findMany('restaurants', { is_active: true });
            if (rests.length) restaurant_id = rests[0].id;
        }
        const id = await store.insertOne('menu_items', {
            name: data.name, price: parseFloat(data.price), restaurant_id,
            description: data.description || '', image_url: data.image_url || null,
            category: data.category || 'main', available: data.available !== false,
            preparation_time: parseInt(data.preparation_time) || 15
        });
        res.json({ success: true, message: 'Menu item created', item_id: id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to create menu item' });
    }
});

app.put('/api/menu/:id', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const item = await store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Menu item not found' });
        await store.updateById('menu_items', req.params.id, req.body);
        res.json({ success: true, message: 'Menu item updated' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update menu item' });
    }
});

app.delete('/api/menu/:id', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        await store.deleteOne('menu_items', { id: req.params.id });
        res.json({ success: true, message: 'Menu item deleted' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to delete menu item' });
    }
});

// ============================================================
// CATEGORIES API — CRUD for admin.html
// ============================================================

app.post('/api/categories', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const { name, description, icon } = req.body;
        if (!name) return res.status(400).json({ success: false, error: 'name is required' });
        const maxOrder = await store.count('categories');
        const id = await store.insertOne('categories', {
            name, description: description || '', icon: icon || '🍽️',
            sort_order: maxOrder + 1, is_active: true
        });
        res.json({ success: true, message: 'Category created', category_id: id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to create category' });
    }
});

app.put('/api/categories/:id', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        await store.updateById('categories', req.params.id, req.body);
        res.json({ success: true, message: 'Category updated' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update category' });
    }
});

app.delete('/api/categories/:id', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        await store.deleteOne('categories', { id: req.params.id });
        res.json({ success: true, message: 'Category deleted' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to delete category' });
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

// Alias used by admin.html
app.post('/api/upload-image', upload.single('file'), (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    if (!req.file) return res.status(400).json({ success: false, error: 'No file uploaded' });
    const filename = `${Date.now()}_${req.file.originalname}`;
    const destPath = path.join(__dirname, '../static/uploads', filename);
    fs.renameSync(req.file.path, destPath);
    res.json({ success: true, url: `/static/uploads/${filename}`, filename });
});

// ============================================================
// DRIVER SEARCH RADIUS SETTINGS
// ============================================================

let driverSearchRadius = 10; // default 10km, kept in-memory

app.get('/api/admin/driver-search-radius', (req, res) => {
    res.json({ success: true, radius: driverSearchRadius });
});

app.put('/api/admin/driver-search-radius', (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    const radius = parseFloat(req.body.radius);
    if (!radius || radius <= 0 || radius > 100) return res.status(400).json({ success: false, error: 'Invalid radius value' });
    driverSearchRadius = radius;
    res.json({ success: true, radius: driverSearchRadius, message: `Search radius updated to ${radius}km` });
});

// ============================================================
// CHANGE PASSWORD
// ============================================================

app.get('/admin/change-password', requireAdmin, (req, res) => {
    res.render('change_password', { error: null, success: null });
});

app.post('/admin/change-password', requireAdmin, async (req, res) => {
    const { current_password, new_password, confirm_password } = req.body;
    try {
        const admin = await store.findById('admin_users', req.session.admin_user_id);
        if (!admin) return res.render('change_password', { error: 'Admin not found', success: null });
        if (admin.password !== current_password) return res.render('change_password', { error: 'Current password is incorrect', success: null });
        if (new_password !== confirm_password) return res.render('change_password', { error: 'Passwords do not match', success: null });
        if (new_password.length < 8) return res.render('change_password', { error: 'Password must be at least 8 characters', success: null });
        await store.updateById('admin_users', admin.id, { password: new_password });
        res.render('change_password', { error: null, success: 'Password changed successfully' });
    } catch (e) {
        console.error(e);
        res.render('change_password', { error: 'Failed to change password', success: null });
    }
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

// ============================================================
// START SERVER
// ============================================================

const PORT = process.env.PORT || 5000;

async function startServer() {
    try {
        await runMigration();
        app.listen(PORT, '0.0.0.0', () => {
            console.log(`ET-FOOD Node.js server running on port ${PORT}`);
            console.log(`Database: Neon PostgreSQL`);
        });
    } catch (err) {
        console.error('Failed to start server:', err.message);
        process.exit(1);
    }
}

startServer();

module.exports = app;
