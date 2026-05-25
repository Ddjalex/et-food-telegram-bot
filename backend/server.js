
const http = require('http');
const express = require('express');
const { Server: SocketIOServer } = require('socket.io');
const session = require('express-session');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const store = require('./store');
const { query } = require('./db');
const { runMigration } = require('./migrate');
const {
    notifyDriverApproved, notifyDriverRejected, notifyDriverNewOrder,
    notifyCustomerOrderStatus, notifyCustomerOrderReceived,
    notifyCustomerKitchenAccepted, notifyCustomerKitchenRejected,
    notifyCustomerPaymentVerified, notifyCustomerDriverAssigned,
    notifyCustomerOrderPickedUp, notifyCustomerOrderDelivered,
    notifyCustomerOrderCancelled, notifyCustomerDeliveryPriceConfirmation,
    notifyKitchenNewOrder
} = require('./notifier');
const { dispatchOrderToDrivers, haversineKm } = require('./driver_assignment');

async function logAudit(req, action, targetType, targetId, targetName, details) {
    try {
        await store.insertOne('audit_logs', {
            admin_id: req.session.admin_id || null,
            admin_username: req.session.admin_username || 'system',
            action,
            target_type: targetType || null,
            target_id: targetId ? String(targetId) : null,
            target_name: targetName || null,
            details: details || null,
            ip_address: req.ip || req.connection.remoteAddress || null
        });
    } catch (e) {
        console.error('Audit log error:', e.message);
    }
}

const app = express();
const httpServer = http.createServer(app);
const io = new SocketIOServer(httpServer, {
    cors: { origin: '*', methods: ['GET', 'POST'] }
});

// In-memory live GPS store: driverId → { lat, lng, orderId, ts }
const liveDriverGPS = new Map();

io.on('connection', (socket) => {
    socket.on('join_order_tracking', ({ orderId }) => {
        if (orderId) socket.join(`order:${orderId}`);
    });

    socket.on('join_kitchen', ({ restaurant_id }) => {
        socket.join('kitchen:all');
        if (restaurant_id) socket.join(`kitchen:${restaurant_id}`);
    });

    socket.on('driver_gps', ({ driverId, orderId, lat, lng }) => {
        if (!lat || !lng) return;
        liveDriverGPS.set(String(driverId), { lat, lng, orderId, ts: Date.now() });
        if (orderId) {
            io.to(`order:${orderId}`).emit('driver_location', { lat, lng, driverId, ts: Date.now() });
        }
        // Persist to DB every ~30s (avoid every-5s writes)
        const key = `loc_saved_${driverId}`;
        const last = global[key] || 0;
        if (Date.now() - last > 30000) {
            global[key] = Date.now();
            store.findOne('drivers', { telegram_user_id: String(driverId) })
                .then(d => d && store.updateById('drivers', d.id, {
                    current_lat: parseFloat(lat), current_lng: parseFloat(lng),
                    last_location_update: new Date()
                })).catch(() => {});
        }
    });
});

// Expose io for use in notifier etc.
app.set('socketio', io);

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.set('view cache', false);

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

// ============================================================
// CUSTOMER PROFILE — fetch by telegram user ID
// ============================================================

app.get('/api/customers/:telegram_user_id', async (req, res) => {
    try {
        const result = await query('SELECT * FROM customers WHERE telegram_user_id = $1', [req.params.telegram_user_id]);
        const customer = result.rows[0];
        if (!customer) return res.json({ success: false, error: 'Customer not found' });
        res.json({ success: true, customer });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch customer' });
    }
});

app.post('/api/customers', async (req, res) => {
    try {
        const { telegram_user_id, name, phone_number } = req.body;
        if (!telegram_user_id) return res.status(400).json({ success: false, error: 'telegram_user_id required' });
        await query(
            `INSERT INTO customers (telegram_user_id, name, phone_number, updated_at)
             VALUES ($1, $2, $3, NOW())
             ON CONFLICT (telegram_user_id) DO UPDATE SET name=$2, phone_number=$3, updated_at=NOW()`,
            [telegram_user_id, name || null, phone_number || null]
        );
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to save customer' });
    }
});

// ============================================================
// SYSTEM SETTINGS — public + super admin
// ============================================================

app.get('/api/settings/delivery-rate', async (req, res) => {
    try {
        const row = await query(`SELECT value FROM system_settings WHERE key = 'price_per_km'`);
        const price_per_km = row.rows[0] ? parseFloat(row.rows[0].value) : 10;
        res.json({ success: true, price_per_km });
    } catch (e) {
        res.json({ success: true, price_per_km: 10 });
    }
});

app.get('/api/super-admin/settings', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const rows = await query(`SELECT key, value FROM system_settings`);
        const settings = {};
        rows.rows.forEach(r => { settings[r.key] = r.value; });
        res.json({ success: true, settings });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to fetch settings' });
    }
});

app.post('/api/super-admin/settings', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const { price_per_km } = req.body;
        if (price_per_km !== undefined) {
            const val = parseFloat(price_per_km);
            if (isNaN(val) || val < 0) return res.status(400).json({ success: false, error: 'Invalid price_per_km' });
            await query(`INSERT INTO system_settings (key, value, updated_at) VALUES ('price_per_km', $1, NOW()) ON CONFLICT (key) DO UPDATE SET value = $1, updated_at = NOW()`, [String(val)]);
        }
        logAudit(req, 'update_settings', 'system', null, 'system_settings', JSON.stringify(req.body));
        res.json({ success: true, message: 'Settings saved' });
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to save settings' });
    }
});

app.get('/api/restaurant-info', async (req, res) => {
    try {
        const restaurants = await store.findMany('restaurants', { is_active: true });
        if (!restaurants.length) {
            return res.json({ success: false, error: 'No restaurants available', company: { name: 'Cloud Kitchen' }, restaurant: { name: 'Restaurant' } });
        }
        const r = restaurants[0];
        res.json({
            success: true,
            company: { name: 'Cloud Kitchen', description: 'Good Food. No Boundaries.' },
            restaurant: { id: r.id, name: r.name, description: r.description, address: r.address, phone: r.phone, logo_url: r.logo_url, cover_image_url: r.cover_image_url, estimated_delivery_time: r.estimated_delivery_time }
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch restaurant information' });
    }
});

// Parse a Google Maps URL and return lat/lng
function parseGoogleMapsUrl(url) {
    if (!url) return null;
    // Match @lat,lng pattern (most common)
    let m = url.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
    if (m) return { lat: parseFloat(m[1]), lng: parseFloat(m[2]) };
    // Match ?q=lat,lng or &q=lat,lng
    m = url.match(/[?&]q=(-?\d+\.\d+),(-?\d+\.\d+)/);
    if (m) return { lat: parseFloat(m[1]), lng: parseFloat(m[2]) };
    // Match ll=lat,lng
    m = url.match(/[?&]ll=(-?\d+\.\d+),(-?\d+\.\d+)/);
    if (m) return { lat: parseFloat(m[1]), lng: parseFloat(m[2]) };
    return null;
}

// Haversine distance in km
function distanceKm(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Parse location URL endpoint
app.post('/api/restaurants/parse-location', async (req, res) => {
    try {
        const { url } = req.body;
        if (!url) return res.status(400).json({ success: false, error: 'url is required' });

        // Try to parse directly first
        let coords = parseGoogleMapsUrl(url);
        if (coords) return res.json({ success: true, ...coords });

        // For short URLs (goo.gl/maps, maps.app.goo.gl), follow the redirect
        const https = require('https');
        const http = require('http');
        const followRedirect = (u, maxRedirects = 5) => new Promise((resolve, reject) => {
            if (maxRedirects === 0) return reject(new Error('Too many redirects'));
            const mod = u.startsWith('https') ? https : http;
            mod.get(u, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (resp) => {
                if (resp.statusCode >= 300 && resp.statusCode < 400 && resp.headers.location) {
                    return resolve(followRedirect(resp.headers.location, maxRedirects - 1));
                }
                resolve(u);
            }).on('error', reject);
        });

        const resolved = await followRedirect(url);
        coords = parseGoogleMapsUrl(resolved);
        if (coords) return res.json({ success: true, ...coords });

        res.status(422).json({ success: false, error: 'Could not extract coordinates from URL. Try a full Google Maps URL.' });
    } catch (e) {
        console.error('parse-location error:', e.message);
        res.status(500).json({ success: false, error: 'Failed to parse location' });
    }
});

app.get('/api/restaurants', async (req, res) => {
    try {
        const customerLat = req.query.lat ? parseFloat(req.query.lat) : null;
        const customerLng = req.query.lng ? parseFloat(req.query.lng) : null;

        const restaurants = await store.findMany('restaurants', { is_active: true });
        let formatted = await Promise.all(restaurants.map(async r => {
            const restLat = r.lat ? parseFloat(r.lat) : null;
            const restLng = r.lng ? parseFloat(r.lng) : null;
            let distance_km = null;
            if (customerLat && customerLng && restLat && restLng) {
                distance_km = Math.round(distanceKm(customerLat, customerLng, restLat, restLng) * 10) / 10;
            }
            return {
                id: r.id, name: r.name, description: r.description || '', address: r.address || '', phone: r.phone || '',
                logo_url: r.logo_url, cover_image_url: r.cover_image_url,
                estimated_delivery_time: r.estimated_delivery_time || '30-45 minutes',
                delivery_fee: parseFloat(r.delivery_fee) || 0, minimum_order: parseFloat(r.minimum_order) || 0,
                is_active: r.is_active !== false,
                menu_items_count: await store.count('menu_items', { restaurant_id: r.id, available: true }),
                rating: parseFloat(r.rating) || 4.5, is_featured: r.is_featured || false,
                lat: restLat, lng: restLng, location_url: r.location_url || null,
                distance_km
            };
        }));

        // Sort by distance if customer location is known
        if (customerLat && customerLng) {
            formatted.sort((a, b) => {
                if (a.distance_km === null && b.distance_km === null) return 0;
                if (a.distance_km === null) return 1;
                if (b.distance_km === null) return -1;
                return a.distance_km - b.distance_km;
            });
        }

        res.json({ success: true, restaurants: formatted, total: formatted.length });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch restaurants' });
    }
});

app.post('/api/restaurants/:id/rate', async (req, res) => {
    try {
        const { id } = req.params;
        const { telegram_user_id, rating } = req.body;
        if (!telegram_user_id) return res.status(400).json({ success: false, error: 'User ID required' });
        const ratingVal = parseInt(rating);
        if (!ratingVal || ratingVal < 1 || ratingVal > 5) return res.status(400).json({ success: false, error: 'Rating must be 1-5' });
        const restaurant = await store.findById('restaurants', id);
        if (!restaurant) return res.status(404).json({ success: false, error: 'Restaurant not found' });

        await query(`
            INSERT INTO restaurant_ratings (restaurant_id, telegram_user_id, rating)
            VALUES ($1, $2, $3)
            ON CONFLICT (restaurant_id, telegram_user_id)
            DO UPDATE SET rating = $3, updated_at = NOW()
        `, [id, telegram_user_id, ratingVal]);

        const result = await query(`SELECT ROUND(AVG(rating)::numeric, 2) as avg_rating, COUNT(*) as total FROM restaurant_ratings WHERE restaurant_id = $1`, [id]);
        const avg = parseFloat(result.rows[0].avg_rating) || ratingVal;
        const count = parseInt(result.rows[0].total) || 1;
        await store.updateById('restaurants', id, { rating: avg, rating_count: count });

        res.json({ success: true, message: 'Rating submitted', new_rating: avg, rating_count: count });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to submit rating' });
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
            // Try to resolve restaurant from the first ordered item's menu entry
            const firstItem = Array.isArray(data.items) && data.items[0];
            const itemId = firstItem && (firstItem.item_id || firstItem.id);
            if (itemId) {
                const menuItem = await store.findById('menu_items', itemId);
                if (menuItem && menuItem.restaurant_id) restaurant_id = menuItem.restaurant_id;
            }
            // Final fallback: first active restaurant sorted by name
            if (!restaurant_id) {
                const rests = await store.findMany('restaurants', { is_active: true }, 'name');
                if (rests.length) restaurant_id = rests[0].id;
                else return res.status(404).json({ success: false, error: 'No restaurants available' });
            }
        }
        const order_id = await store.insertOne('orders', {
            customer_name: data.customer_name,
            customer_phone: data.customer_phone,
            customer_address: data.customer_address,
            restaurant_id,
            telegram_user_id: data.telegram_user_id,
            items: data.items,
            total_amount: data.total_amount || 0,
            delivery_fee: data.estimated_driver_fee || 0,
            driver_distance_km: data.driver_distance_km || 0,
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

        // Real-time push to kitchen dashboard via Socket.io
        const ioInstance = app.get('socketio');
        if (ioInstance) {
            const kitchenRoom = order.restaurant_id ? `kitchen:${order.restaurant_id}` : 'kitchen:all';
            ioInstance.to(kitchenRoom).to('kitchen:all').emit('new_order', order);
        }

        // Notify customer that order was received
        if (order.telegram_user_id) {
            notifyCustomerOrderReceived(order.telegram_user_id, order).catch(e => console.error('notify error:', e.message));
        }

        // Notify kitchen staff via Telegram
        (async () => {
            try {
                const staffFilter = { role: 'kitchen', is_active: true };
                if (restaurant_id) staffFilter.restaurant_id = restaurant_id;
                const kitchenStaff = await store.findMany('admin_users', staffFilter);
                if (kitchenStaff.length > 0) {
                    await notifyKitchenNewOrder(kitchenStaff, order);
                } else {
                    // Fall back to all admins if no kitchen staff found
                    const admins = await store.findMany('admin_users', { is_active: true });
                    const eligible = admins.filter(u => ['kitchen','admin','superadmin'].includes(u.role) && u.telegram_user_id);
                    if (eligible.length) await notifyKitchenNewOrder(eligible, order);
                }
            } catch (e) {
                console.error('Kitchen notify error:', e.message);
            }
        })();
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

// Driver marks order as delivered — calculates fee and sends customer price confirmation
app.post('/api/orders/:id/delivered', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });

        // Calculate driver fee: distance × price_per_km
        let driverFee = parseFloat(order.driver_fee || order.delivery_fee || 0);
        let distanceKmValue = parseFloat(order.driver_distance_km || 0);

        try {
            const rateRow = await query(`SELECT value FROM system_settings WHERE key = 'price_per_km'`);
            const pricePerKm = rateRow.rows[0] ? parseFloat(rateRow.rows[0].value) : 10;
            const restaurant = order.restaurant_id
                ? await store.findById('restaurants', order.restaurant_id).catch(() => null)
                : null;
            const restLat = restaurant ? parseFloat(restaurant.lat) : null;
            const restLng = restaurant ? parseFloat(restaurant.lng) : null;
            const custLat = order.location_lat ? parseFloat(order.location_lat) : null;
            const custLng = order.location_lng ? parseFloat(order.location_lng) : null;

            if (restLat && restLng && custLat && custLng) {
                const calcDist = haversineKm(restLat, restLng, custLat, custLng);
                distanceKmValue = Math.round(calcDist * 10) / 10;
                driverFee = Math.round(calcDist * pricePerKm * 10) / 10;
            }
        } catch (feeErr) {
            console.error('Driver fee calc error:', feeErr.message);
        }

        // Update order: mark delivered, store calculated fee, update total to include delivery fee
        const foodSubtotal = parseFloat(order.total_amount || 0);
        const grandTotal = foodSubtotal + driverFee;
        await store.updateById('orders', order.id, {
            status: 'delivered',
            driver_fee: driverFee,
            driver_distance_km: distanceKmValue,
            total_amount: grandTotal
        });

        const updated = await store.findById('orders', order.id);
        res.json({ success: true, order: updated, driver_fee: driverFee, distance_km: distanceKmValue });

        // Send customer a detailed price breakdown with Accept button
        if (updated.telegram_user_id) {
            notifyCustomerDeliveryPriceConfirmation(updated.telegram_user_id, updated)
                .catch(e => console.error('delivery price notification error:', e.message));
        }

        // Mark driver as available again
        if (order.driver_id) {
            store.updateById('drivers', order.driver_id, { is_available: true, is_active: true })
                .catch(e => console.error('driver availability reset error:', e.message));
        }
    } catch (e) {
        console.error('Delivered endpoint error:', e);
        res.status(500).json({ success: false, error: 'Failed to mark order as delivered' });
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
            req.session.admin_restaurant_id = admin.restaurant_id || null;
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
            lat: r.lat || null,
            lng: r.lng || null,
            location_url: r.location_url || null,
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

        // Auto-parse location URL if provided
        let lat = data.lat ? parseFloat(data.lat) : null;
        let lng = data.lng ? parseFloat(data.lng) : null;
        const location_url = data.location_url || null;
        if (location_url && (!lat || !lng)) {
            const coords = parseGoogleMapsUrl(location_url);
            if (coords) { lat = coords.lat; lng = coords.lng; }
        }

        const id = await store.insertOne('restaurants', {
            name: data.name, address: data.address, phone: data.phone,
            description: data.description || '',
            estimated_delivery_time: data.estimated_delivery_time || '30-45 minutes',
            delivery_fee: parseFloat(data.delivery_fee) || 0,
            minimum_order: parseFloat(data.minimum_order) || 0,
            is_active: data.is_active !== false,
            is_featured: data.is_featured || false,
            logo_url: data.logo_url || null, cover_image_url: data.cover_image_url || null,
            lat, lng, location_url
        });
        logAudit(req, 'create_restaurant', 'restaurant', id, data.name);
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
        logAudit(req, 'edit_restaurant', 'restaurant', r.id, r.name, `Updated fields: ${Object.keys(req.body).join(', ')}`);
        res.json({ success: true, message: 'Restaurant updated successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to update restaurant' });
    }
});

app.delete('/api/restaurants/super-admin/:id', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const rDel = await store.findById('restaurants', req.params.id);
        await store.deleteOne('restaurants', { id: req.params.id });
        logAudit(req, 'delete_restaurant', 'restaurant', req.params.id, rDel ? rDel.name : req.params.id);
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
                id: a.id, username: a.username, full_name: a.full_name || '',
                email: a.email || '', phone: a.phone || '',
                role: a.role || 'admin',
                restaurant_id: a.restaurant_id, restaurant_name,
                is_active: a.is_active !== false,
                is_blocked: a.is_blocked === true,
                last_login: a.last_login || null,
                created_at: a.created_at
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
        logAudit(req, 'create_admin', 'admin', id, data.username, `Role: ${data.role || 'admin'}`);
        res.json({ success: true, message: `Admin ${data.username} created successfully`, admin_id: id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to create admin' });
    }
});

app.put('/api/super-admin/admins/:id', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const a = await store.findById('admin_users', req.params.id);
        if (!a) return res.status(404).json({ success: false, error: 'Admin not found' });
        const { username, full_name, email, phone, role, restaurant_id, password } = req.body;
        const updates = {};
        if (username) updates.username = username;
        if (full_name) updates.full_name = full_name;
        if (email !== undefined) updates.email = email;
        if (phone !== undefined) updates.phone = phone;
        if (role) updates.role = role;
        if (restaurant_id !== undefined) updates.restaurant_id = restaurant_id || null;
        if (password) updates.password = password;
        await store.updateById('admin_users', req.params.id, updates);
        logAudit(req, 'edit_admin', 'admin', a.id, a.username, `Updated fields: ${Object.keys(updates).join(', ')}`);
        res.json({ success: true, message: 'Admin updated successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to update admin' });
    }
});

app.delete('/api/super-admin/admins/:id', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const a = await store.findById('admin_users', req.params.id);
        if (!a) return res.status(404).json({ success: false, error: 'Admin not found' });
        if (a.role === 'superadmin') return res.status(403).json({ success: false, message: 'Cannot delete superadmin account' });
        await store.deleteOne('admin_users', { id: req.params.id });
        logAudit(req, 'delete_admin', 'admin', a.id, a.username, `Role was: ${a.role}`);
        res.json({ success: true, message: `Admin "${a.username}" deleted successfully` });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to delete admin' });
    }
});

app.post('/api/super-admin/admins/:id/block', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const a = await store.findById('admin_users', req.params.id);
        if (!a) return res.status(404).json({ success: false, error: 'Admin not found' });
        if (a.role === 'superadmin') return res.status(403).json({ success: false, message: 'Cannot block superadmin account' });
        const blocked = req.body.blocked === true;
        await store.updateById('admin_users', req.params.id, { is_active: !blocked, is_blocked: blocked });
        logAudit(req, blocked ? 'block_admin' : 'unblock_admin', 'admin', a.id, a.username);
        res.json({ success: true, message: `Admin ${blocked ? 'blocked' : 'unblocked'} successfully` });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, message: 'Failed to update admin status' });
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

app.get('/api/super-admin/audit-logs', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const limit = parseInt(req.query.limit) || 100;
        const offset = parseInt(req.query.offset) || 0;
        const action = req.query.action || null;
        const target_type = req.query.target_type || null;

        let sql = `SELECT * FROM audit_logs`;
        const conditions = [];
        const values = [];
        if (action) { values.push(action); conditions.push(`action = $${values.length}`); }
        if (target_type) { values.push(target_type); conditions.push(`target_type = $${values.length}`); }
        if (conditions.length) sql += ` WHERE ${conditions.join(' AND ')}`;
        sql += ` ORDER BY created_at DESC LIMIT $${values.length + 1} OFFSET $${values.length + 2}`;
        values.push(limit, offset);

        const { query } = require('./db');
        const result = await query(sql, values);
        const countResult = await query('SELECT COUNT(*) FROM audit_logs');
        res.json({ success: true, logs: result.rows, total: parseInt(countResult.rows[0].count) });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch audit logs' });
    }
});

app.delete('/api/super-admin/audit-logs', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const { query } = require('./db');
        await query('DELETE FROM audit_logs');
        res.json({ success: true, message: 'Audit logs cleared successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to clear audit logs' });
    }
});

app.get('/api/super-admin/orders', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const { status, restaurant_id } = req.query;
        let filter = {};
        if (status) filter.status = status;
        if (restaurant_id) filter.restaurant_id = restaurant_id;

        const [orders, restaurants, drivers] = await Promise.all([
            store.findMany('orders', filter, 'created_at'),
            store.findMany('restaurants', {}),
            store.findMany('drivers', {})
        ]);

        const restMap = {};
        for (const r of restaurants) restMap[r.id] = r.name;
        const driverMap = {};
        for (const d of drivers) driverMap[d.id] = d.name;

        const enriched = orders
            .map(o => ({
                ...o,
                restaurant_name: restMap[o.restaurant_id] || 'Unknown',
                driver_name: o.driver_id ? (driverMap[o.driver_id] || 'Unknown') : null
            }))
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        const stats = {
            total: enriched.length,
            pending: enriched.filter(o => o.status === 'pending').length,
            preparing: enriched.filter(o => ['confirmed', 'preparing', 'kitchen_confirmed', 'ready'].includes(o.status)).length,
            out_for_delivery: enriched.filter(o => o.status === 'out_for_delivery').length,
            completed: enriched.filter(o => o.status === 'delivered').length,
            cancelled: enriched.filter(o => o.status === 'cancelled').length
        };

        res.json({ success: true, orders: enriched, stats });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch orders' });
    }
});

app.patch('/api/super-admin/orders/:id/status', async (req, res) => {
    if (!checkAdminSession(req) || req.session.admin_role !== 'superadmin') return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const { status } = req.body;
        if (!status) return res.status(400).json({ success: false, error: 'status is required' });
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        const prevStatus = order.status;
        await store.updateById('orders', req.params.id, { status });
        logAudit(req, 'update_order_status', 'order', req.params.id, req.params.id, `Status → ${status}`);
        res.json({ success: true, message: 'Order status updated' });

        // Fire customer notification after response
        if (order.telegram_user_id && status !== prevStatus) {
            const updated = { ...order, status };
            if (status === 'delivered') {
                // Calculate actual driver fee based on distance × price_per_km and save to order
                (async () => {
                    try {
                        const rateRow = await query(`SELECT value FROM system_settings WHERE key = 'price_per_km'`);
                        const pricePerKm = rateRow.rows[0] ? parseFloat(rateRow.rows[0].value) : 10;
                        const restaurant = order.restaurant_id ? await store.findById('restaurants', order.restaurant_id).catch(() => null) : null;
                        const restLat = restaurant ? parseFloat(restaurant.lat) : null;
                        const restLng = restaurant ? parseFloat(restaurant.lng) : null;
                        const custLat = order.location_lat ? parseFloat(order.location_lat) : null;
                        const custLng = order.location_lng ? parseFloat(order.location_lng) : null;
                        if (restLat && restLng && custLat && custLng) {
                            const actualDist = distanceKm(restLat, restLng, custLat, custLng);
                            const actualFee = Math.round(actualDist * pricePerKm * 10) / 10;
                            await store.updateById('orders', order.id, {
                                driver_fee: actualFee,
                                driver_distance_km: Math.round(actualDist * 10) / 10
                            });
                        }
                    } catch (e) { console.error('driver fee calc error:', e.message); }
                })();
                notifyCustomerOrderDelivered(order.telegram_user_id, updated).catch(e => console.error('notify error:', e.message));
            } else if (status === 'cancelled') {
                notifyCustomerOrderCancelled(order.telegram_user_id, updated, req.body.reason).catch(e => console.error('notify error:', e.message));
            } else if (status === 'kitchen_confirmed' || status === 'confirmed' || status === 'preparing') {
                notifyCustomerKitchenAccepted(order.telegram_user_id, updated).catch(e => console.error('notify error:', e.message));
            } else if (status === 'out_for_delivery') {
                let driver = null;
                if (order.driver_id) driver = await store.findById('drivers', order.driver_id).catch(() => null);
                notifyCustomerOrderPickedUp(order.telegram_user_id, updated, driver).catch(e => console.error('notify error:', e.message));
            }
        }
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update order status' });
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
        try { notifyDriverApproved(driver); } catch (_) {}
        logAudit(req, 'approve_driver', 'driver', driver.id, driver.name);
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
        const reason = req.body.reason || 'Does not meet current requirements';
        await store.updateById('drivers', req.params.id, { is_approved: false, is_active: false, rejection_reason: reason });
        try { notifyDriverRejected(driver, reason); } catch (_) {}
        logAudit(req, 'reject_driver', 'driver', driver.id, driver.name, `Reason: ${reason}`);
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
        logAudit(req, 'delete_driver', 'driver', driver.id, driver.name);
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
// ADMIN SESSION INFO
// ============================================================

app.get('/api/admin/me', async (req, res) => {
    if (!checkAdminSession(req)) return res.status(401).json({ success: false, error: 'Unauthorized' });
    try {
        const admin = await store.findById('admin_users', req.session.admin_user_id);
        res.json({
            success: true,
            admin: {
                id: req.session.admin_user_id,
                username: req.session.admin_username,
                role: req.session.admin_role,
                restaurant_id: admin ? admin.restaurant_id : req.session.admin_restaurant_id,
                full_name: admin ? admin.full_name : null
            }
        });
    } catch (e) {
        res.json({
            success: true,
            admin: {
                id: req.session.admin_user_id,
                username: req.session.admin_username,
                role: req.session.admin_role,
                restaurant_id: req.session.admin_restaurant_id || null
            }
        });
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
        if (user && user.password === password && (user.role === 'kitchen' || user.role === 'kitchen_staff' || user.role === 'admin' || user.role === 'superadmin')) {
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

// Shared kitchen order status update logic
async function kitchenOrderStatusHandler(req, res, orderId, body, session) {
    try {
        const order = await store.findById('orders', orderId);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        const prevStatus = order.status;
        await store.updateById('orders', orderId, body);
        const updated = await store.findById('orders', orderId);
        res.json({ success: true, order: updated });

        const newStatus = body.status;
        if (updated.telegram_user_id && newStatus && newStatus !== prevStatus) {
            if (newStatus === 'kitchen_confirmed' || newStatus === 'confirmed') {
                notifyCustomerKitchenAccepted(updated.telegram_user_id, updated).catch(e => console.error('notify error:', e.message));
            } else if (newStatus === 'preparing') {
                notifyCustomerOrderStatus(updated.telegram_user_id, updated, '👨‍🍳 Your food is being prepared! We\'ll notify you when it\'s ready.').catch(e => console.error('notify error:', e.message));
            } else if (newStatus === 'ready') {
                notifyCustomerOrderStatus(updated.telegram_user_id, updated, '📦 Your food is ready! A driver is on the way to pick it up...').catch(e => console.error('notify error:', e.message));
                dispatchOrderToDrivers(updated).catch(e => console.error('[DriverAssignment] dispatch error:', e.message));
            } else if (newStatus === 'unavailable' || newStatus === 'cancelled') {
                const reason = body.rejection_reason || body.cancel_reason || body.reason || 'Item unavailable';
                notifyCustomerKitchenRejected(updated.telegram_user_id, updated, reason).catch(e => console.error('notify error:', e.message));
            }
        }
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update order' });
    }
}

// PATCH — used by older code paths
app.patch('/api/kitchen/orders/:id', requireKitchen, (req, res) => {
    kitchenOrderStatusHandler(req, res, req.params.id, req.body, req.session);
});

// POST /api/kitchen/orders/:id/status — used by kitchen dashboard JS
app.post('/api/kitchen/orders/:id/status', requireKitchen, (req, res) => {
    kitchenOrderStatusHandler(req, res, req.params.id, req.body, req.session);
});

app.get('/api/kitchen/menu-items', requireKitchen, async (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const filter = restaurant_id ? { restaurant_id } : {};
        const items = await store.findMany('menu_items', filter);
        res.json({ success: true, items, menu_items: items });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch menu items' });
    }
});

app.post('/api/kitchen/toggle-availability', requireKitchen, async (req, res) => {
    try {
        const { item_id, available } = req.body;
        const item = await store.findById('menu_items', item_id);
        if (!item) return res.status(404).json({ success: false, error: 'Item not found' });
        await store.updateById('menu_items', item_id, { available: !!available });
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update availability' });
    }
});

app.post('/api/kitchen/bulk-update-availability', requireKitchen, async (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const { action, category } = req.body;
        const { query: dbQuery } = require('./db');
        if (action === 'mark_all_available') {
            const q = restaurant_id
                ? `UPDATE menu_items SET available = true WHERE restaurant_id = $1`
                : `UPDATE menu_items SET available = true`;
            await dbQuery(q, restaurant_id ? [restaurant_id] : []);
        } else if (action === 'mark_all_unavailable') {
            const q = restaurant_id
                ? `UPDATE menu_items SET available = false WHERE restaurant_id = $1`
                : `UPDATE menu_items SET available = false`;
            await dbQuery(q, restaurant_id ? [restaurant_id] : []);
        } else if (action === 'mark_category_unavailable' && category) {
            const q = restaurant_id
                ? `UPDATE menu_items SET available = false WHERE category = $1 AND restaurant_id = $2`
                : `UPDATE menu_items SET available = false WHERE category = $1`;
            await dbQuery(q, restaurant_id ? [category, restaurant_id] : [category]);
        } else {
            return res.status(400).json({ success: false, error: 'Invalid action' });
        }
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to bulk update availability' });
    }
});

app.get('/api/kitchen/categories', requireKitchen, async (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const filter = restaurant_id ? { restaurant_id } : {};
        const items = await store.findMany('menu_items', filter);
        const cats = [...new Set(items.map(i => i.category).filter(Boolean))].map(name => ({ name }));
        res.json({ success: true, categories: cats });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch categories' });
    }
});

app.post('/api/kitchen/products', requireKitchen, upload.single('image'), async (req, res) => {
    try {
        const restaurant_id = req.session.kitchen_restaurant_id;
        const { name, description, price, category } = req.body;
        if (!name || !price) return res.status(400).json({ success: false, error: 'Name and price are required' });
        let image_url = null;
        if (req.file) image_url = '/static/uploads/' + req.file.filename;
        const { v4: uuidv4 } = require('uuid');
        await store.insertOne('menu_items', {
            id: uuidv4(), restaurant_id, name, description: description || '',
            price: parseFloat(price), category: category || '', image_url, available: true,
            preparation_time: 15, ingredients: [], allergens: [], nutritional_info: {}
        });
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to create product' });
    }
});

app.put('/api/kitchen/products/:id', requireKitchen, upload.single('image'), async (req, res) => {
    try {
        const item = await store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Product not found' });
        const { name, description, price, category } = req.body;
        const updates = { name, description, price: parseFloat(price), category };
        if (req.file) updates.image_url = '/static/uploads/' + req.file.filename;
        await store.updateById('menu_items', req.params.id, updates);
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update product' });
    }
});

app.delete('/api/kitchen/products/:id', requireKitchen, async (req, res) => {
    try {
        const item = await store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Product not found' });
        await store.deleteById('menu_items', req.params.id);
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to delete product' });
    }
});

app.post('/api/kitchen/products/:id/price', requireKitchen, async (req, res) => {
    try {
        const item = await store.findById('menu_items', req.params.id);
        if (!item) return res.status(404).json({ success: false, error: 'Product not found' });
        const { price } = req.body;
        if (!price || isNaN(parseFloat(price))) return res.status(400).json({ success: false, error: 'Invalid price' });
        await store.updateById('menu_items', req.params.id, { price: parseFloat(price) });
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update price' });
    }
});

// Kitchen confirm availability — "Available - Send Payment" / "Unavailable" buttons
app.post('/api/kitchen/confirm-availability/:id', requireKitchen, async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        const { available, reason } = req.body;

        if (available) {
            await store.updateById('orders', req.params.id, { status: 'kitchen_confirmed' });
            const updated = await store.findById('orders', req.params.id);
            res.json({ success: true, message: 'Order confirmed! Notifying nearby drivers.' });

            // Notify customer
            if (updated.telegram_user_id) {
                notifyCustomerKitchenAccepted(updated.telegram_user_id, updated).catch(e => console.error('notify customer error:', e.message));
            }
            // NOTE: Do NOT dispatch drivers here — dispatch happens when kitchen marks 'ready'
        } else {
            const cancelReason = reason || 'Item unavailable';
            await store.updateById('orders', req.params.id, { status: 'cancelled', rejection_reason: cancelReason });
            const updated = await store.findById('orders', req.params.id);
            res.json({ success: true, message: 'Order marked as unavailable.' });

            if (updated.telegram_user_id) {
                notifyCustomerKitchenRejected(updated.telegram_user_id, updated, cancelReason).catch(e => console.error('notify customer error:', e.message));
            }
        }
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to process availability' });
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
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.set('Pragma', 'no-cache');
    res.set('Expires', '0');
    res.sendFile(path.join(__dirname, '../frontend/enhanced_driver_panel.html'));
});

// ===== CUSTOMER LIVE LOCATION API =====

app.get('/api/customer-location/:telegramId', async (req, res) => {
    try {
        const { query: dbQuery } = require('./db');
        const result = await dbQuery(
            `SELECT * FROM customer_live_locations WHERE telegram_user_id = $1`,
            [String(req.params.telegramId)]
        );
        const row = result.rows[0];
        if (!row) return res.json({ success: true, location: null });
        const isExpired = row.expires_at && new Date(row.expires_at) < new Date();
        if (isExpired) return res.json({ success: true, location: null, expired: true });
        const isLive = row.live_period > 0;
        res.json({
            success: true,
            location: {
                lat: parseFloat(row.lat),
                lng: parseFloat(row.lng),
                is_live: isLive,
                live_period: row.live_period,
                updated_at: row.updated_at,
                expires_at: row.expires_at
            }
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch customer location' });
    }
});

// Fetch orders by a list of IDs (for browser / non-Telegram fallback)
app.get('/api/customer/orders/by-ids', async (req, res) => {
    try {
        const ids = (req.query.ids || '').split(',').map(s => s.trim()).filter(Boolean).slice(0, 30);
        if (!ids.length) return res.json({ success: true, orders: [] });
        const orders = await Promise.all(ids.map(id => store.findById('orders', id).catch(() => null)));
        res.json({ success: true, orders: orders.filter(Boolean) });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch orders' });
    }
});

app.get('/api/customer/orders/:telegramId', async (req, res) => {
    try {
        const orders = await store.findMany('orders', { telegram_user_id: String(req.params.telegramId) }, 'created_at');
        const sorted = orders.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        res.json({ success: true, orders: sorted.slice(0, 20) });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch customer orders' });
    }
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

// Customer live tracking page
app.get('/tracking/:orderId', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/live-tracking.html'));
});

// Live driver GPS from memory (for tracking page polling fallback)
app.get('/api/orders/:id/driver-location', (req, res) => {
    try {
        const cached = [...liveDriverGPS.values()].find(v => v.orderId === req.params.id);
        if (cached && Date.now() - cached.ts < 15000) {
            return res.json({ success: true, lat: cached.lat, lng: cached.lng, fresh: true });
        }
        res.json({ success: false, fresh: false });
    } catch (e) {
        res.status(500).json({ success: false });
    }
});

// Mark order as picked up from restaurant — driver has the food, heading to customer
app.post('/api/orders/:id/pickup', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });

        // Broadcast to tracking room
        io.to(`order:${order.id}`).emit('order_status', { status: 'picked_up', orderId: order.id });
        res.json({ success: true });

        // Notify customer that driver has the food and is on the way
        if (order.telegram_user_id) {
            let driver = null;
            if (order.driver_id) driver = await store.findById('drivers', order.driver_id).catch(() => null);
            notifyCustomerOrderPickedUp(order.telegram_user_id, order, driver)
                .catch(e => console.error('pickup notify error:', e.message));
        }
    } catch (e) {
        res.status(500).json({ success: false, error: 'Failed to mark pickup' });
    }
});

app.get('/api/orders/:id/tracking', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });

        let driver = null;
        if (order.driver_id) {
            const d = await store.findById('drivers', order.driver_id);
            if (d) driver = {
                id: d.id, name: d.name, phone: d.phone_number,
                vehicle_type: d.vehicle_type,
                current_lat: d.current_lat ? parseFloat(d.current_lat) : null,
                current_lng: d.current_lng ? parseFloat(d.current_lng) : null,
                last_location_update: d.last_location_update
            };
        }

        let restaurant = null;
        if (order.restaurant_id) {
            const r = await store.findById('restaurants', order.restaurant_id);
            if (r) restaurant = {
                name: r.name, address: r.address,
                lat: r.lat ? parseFloat(r.lat) : 9.0248,
                lng: r.lng ? parseFloat(r.lng) : 38.7468
            };
        }

        res.json({
            success: true,
            order: {
                id: order.id, order_number: order.order_number, status: order.status,
                customer_name: order.customer_name,
                customer_lat: order.location_lat ? parseFloat(order.location_lat) : null,
                customer_lng: order.location_lng ? parseFloat(order.location_lng) : null,
                total_amount: order.total_amount, payment_method: order.payment_method,
                created_at: order.created_at
            },
            driver,
            restaurant
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch tracking info' });
    }
});

app.put('/api/orders/:id/status', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        const prevStatus = order.status;
        const newStatus = req.body.status;
        await store.updateById('orders', req.params.id, { status: newStatus });
        const updated = await store.findById('orders', req.params.id);
        res.json({ success: true, order: updated });

        // Fire notifications after response
        if (updated.telegram_user_id && newStatus && newStatus !== prevStatus) {
            if (newStatus === 'delivered') {
                notifyCustomerOrderDelivered(updated.telegram_user_id, updated).catch(e => console.error('notify error:', e.message));
            } else if (newStatus === 'cancelled') {
                notifyCustomerOrderCancelled(updated.telegram_user_id, updated, req.body.reason).catch(e => console.error('notify error:', e.message));
            } else if (newStatus === 'kitchen_confirmed' || newStatus === 'confirmed' || newStatus === 'preparing') {
                notifyCustomerKitchenAccepted(updated.telegram_user_id, updated).catch(e => console.error('notify error:', e.message));
            } else if (newStatus === 'out_for_delivery') {
                let driver = null;
                if (updated.driver_id) driver = await store.findById('drivers', updated.driver_id).catch(() => null);
                notifyCustomerOrderPickedUp(updated.telegram_user_id, updated, driver).catch(e => console.error('notify error:', e.message));
            } else if (newStatus === 'ready') {
                notifyCustomerOrderStatus(updated.telegram_user_id, updated, '🔔 Your order is ready and waiting for a driver!').catch(e => console.error('notify error:', e.message));
            }
        }
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
// DRIVER TELEGRAM-BASED ENDPOINTS (used by driver Mini WebApp)
// ============================================================

app.get('/api/drivers/telegram/:telegramId', async (req, res) => {
    try {
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });
        res.json(driver);
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch driver' });
    }
});

app.get('/api/drivers/telegram/:telegramId/status', async (req, res) => {
    try {
        res.set('Cache-Control', 'no-store, no-cache, must-revalidate');
        res.set('Pragma', 'no-cache');
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });
        console.log(`[DriverStatus] ${driver.name} (${req.params.telegramId}) is_available=${driver.is_available}`);
        res.json({
            driver_id: driver.id,
            name: driver.name,
            is_available: driver.is_available,
            is_approved: driver.is_approved,
            is_active: driver.is_active,
            current_lat: driver.current_lat,
            current_lng: driver.current_lng,
            last_location_update: driver.last_location_update,
            total_deliveries: driver.total_deliveries || 0,
            rating: driver.rating || 5.0
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch driver status' });
    }
});

app.post('/api/drivers/telegram/:telegramId/toggle', async (req, res) => {
    try {
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });
        if (!driver.is_approved) return res.status(403).json({ success: false, error: 'Account not approved yet' });
        await store.updateById('drivers', driver.id, { is_available: req.body.is_available });
        res.json({ success: true, is_available: req.body.is_available });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to toggle status' });
    }
});

app.post('/api/drivers/telegram/:telegramId/location', async (req, res) => {
    try {
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });
        const { lat, lng } = req.body;
        await store.updateById('drivers', driver.id, {
            current_lat: parseFloat(lat),
            current_lng: parseFloat(lng),
            last_location_update: new Date()
        });
        res.json({ success: true });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to update location' });
    }
});

app.get('/api/drivers/telegram/:telegramId/orders', async (req, res) => {
    try {
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });
        const allOrders = await store.findMany('orders', {}, 'created_at');
        const driverOrders = allOrders.filter(o =>
            o.driver_id === driver.id ||
            // Show kitchen_confirmed orders (awaiting driver pickup) to available drivers
            (o.status === 'kitchen_confirmed' && !o.driver_id && driver.is_available && driver.is_approved) ||
            o.status === 'out_for_delivery' ||
            o.status === 'ready'
        );
        res.json({ success: true, orders: driverOrders, driver_id: driver.id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch orders' });
    }
});

app.get('/api/drivers/telegram/:telegramId/earnings', async (req, res) => {
    try {
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });

        const allOrders = await store.findMany('orders', {}, 'created_at');
        const delivered = allOrders.filter(o => o.driver_id === driver.id && o.status === 'delivered');

        const now = new Date();
        const startOfDay   = new Date(now); startOfDay.setHours(0,0,0,0);
        const startOfWeek  = new Date(now); startOfWeek.setDate(now.getDate() - now.getDay()); startOfWeek.setHours(0,0,0,0);
        const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

        const calc = (orders) => {
            const fee   = orders.reduce((s, o) => s + parseFloat(o.driver_fee || 0), 0);
            const dist  = orders.reduce((s, o) => s + parseFloat(o.driver_distance_km || 0), 0);
            return { count: orders.length, fee: Math.round(fee * 10) / 10, distance: Math.round(dist * 10) / 10 };
        };

        const todayOrders  = delivered.filter(o => new Date(o.created_at) >= startOfDay);
        const weekOrders   = delivered.filter(o => new Date(o.created_at) >= startOfWeek);
        const monthOrders  = delivered.filter(o => new Date(o.created_at) >= startOfMonth);

        // Build recent delivery history (last 20)
        const recent = delivered
            .slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .slice(0, 20)
            .map(o => ({
                id: o.id,
                order_number: o.order_number,
                customer_name: o.customer_name,
                created_at: o.created_at,
                driver_fee: parseFloat(o.driver_fee || 0),
                driver_distance_km: parseFloat(o.driver_distance_km || 0),
                total_amount: parseFloat(o.total_amount || 0)
            }));

        res.json({
            success: true,
            today:   calc(todayOrders),
            week:    calc(weekOrders),
            month:   calc(monthOrders),
            allTime: calc(delivered),
            recent
        });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch earnings' });
    }
});

app.post('/api/drivers/telegram/:telegramId/sos', async (req, res) => {
    try {
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });

        const { lat, lng } = req.body;

        // Get all admin telegram IDs
        const admins = await store.findMany('admin_users', {});
        const adminIds = admins
            .filter(a => a.telegram_user_id)
            .map(a => a.telegram_user_id);

        if (adminIds.length === 0) {
            return res.json({ success: true, sent: 0, message: 'No admin Telegram IDs configured' });
        }

        const { notifyDriverSOS } = require('./notifier');
        await notifyDriverSOS(adminIds, driver, lat, lng);

        res.json({ success: true, sent: adminIds.length });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to send SOS' });
    }
});

app.get('/api/drivers/telegram/:telegramId/documents', async (req, res) => {
    try {
        const driver = await store.findOne('drivers', { telegram_user_id: String(req.params.telegramId) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });
        const docs = await store.findMany('driver_documents', { driver_id: driver.id }, 'uploaded_at');
        res.json({ success: true, documents: docs, driver_id: driver.id });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to fetch documents' });
    }
});

app.post('/api/orders/:id/accept', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        const { driver_telegram_id } = req.body;
        let driverUpdate = { status: 'out_for_delivery' };
        let assignedDriver = null;
        if (driver_telegram_id) {
            const driver = await store.findOne('drivers', { telegram_user_id: String(driver_telegram_id) });
            if (driver) {
                driverUpdate.driver_id = driver.id;
                assignedDriver = driver;
                await store.updateById('drivers', driver.id, { is_available: false });
            }
        }
        await store.updateById('orders', req.params.id, driverUpdate);
        const updated = await store.findById('orders', req.params.id);
        res.json({ success: true, ...updated });

        // Notify customer that driver accepted and is on the way
        if (updated.telegram_user_id) {
            if (assignedDriver) {
                notifyCustomerDriverAssigned(updated.telegram_user_id, updated, assignedDriver).catch(e => console.error('notify error:', e.message));
            } else {
                notifyCustomerOrderPickedUp(updated.telegram_user_id, updated, null).catch(e => console.error('notify error:', e.message));
            }
        }
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to accept order' });
    }
});

app.post('/api/orders/:id/reject', async (req, res) => {
    try {
        const order = await store.findById('orders', req.params.id);
        if (!order) return res.status(404).json({ success: false, error: 'Order not found' });
        res.json({ success: true, message: 'Order rejected — looking for another driver' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to reject order' });
    }
});

// Public endpoint — no admin session needed, driver identifies by telegram ID
app.post('/api/driver/upload-document', upload.single('document'), async (req, res) => {
    try {
        if (!req.file) return res.status(400).json({ success: false, error: 'No file uploaded' });
        const { telegram_user_id, doc_type } = req.body;
        if (!telegram_user_id) return res.status(400).json({ success: false, error: 'telegram_user_id required' });

        const driver = await store.findOne('drivers', { telegram_user_id: String(telegram_user_id) });
        if (!driver) return res.status(404).json({ success: false, error: 'Driver not found' });

        const filename = `doc_${driver.id}_${Date.now()}_${req.file.originalname}`;
        const destDir = path.join(__dirname, '../static/driver_documents');
        if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });
        fs.renameSync(req.file.path, path.join(destDir, filename));

        const url = `/static/driver_documents/${filename}`;
        const docId = await store.insertOne('driver_documents', {
            driver_id: driver.id,
            doc_type: doc_type || 'document',
            file_url: url,
            filename,
            uploaded_at: new Date()
        });

        res.json({ success: true, url, doc_id: docId, message: 'Document uploaded successfully' });
    } catch (e) {
        console.error(e);
        res.status(500).json({ success: false, error: 'Failed to upload document' });
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
        httpServer.listen(PORT, '0.0.0.0', () => {
            console.log(`Cloud Kitchen server running on port ${PORT}`);
            console.log(`Database: Neon PostgreSQL`);
        });
    } catch (err) {
        console.error('Failed to start server:', err.message);
        process.exit(1);
    }
}

startServer();

module.exports = { app, io };
