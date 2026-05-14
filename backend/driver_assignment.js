const { query } = require('./db');
const store = require('./store');
const { notifyDriverNewOrder } = require('./notifier');

// Haversine formula — returns distance in km between two lat/lng points
function haversineKm(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// Find up to `limit` nearest available approved drivers within 10 km
async function findNearestDrivers(refLat, refLng, limit = 3) {
    if (!refLat || !refLng) {
        // No reference location — just return any available approved drivers
        return store.findMany('drivers', { is_available: true, is_approved: true }, null, limit);
    }

    const result = await query(
        `SELECT * FROM drivers
         WHERE is_available = true
           AND is_approved = true
           AND current_lat IS NOT NULL
           AND current_lng IS NOT NULL`
    );

    const drivers = result.rows;
    const withDistance = drivers
        .map(d => ({ ...d, distance_km: haversineKm(refLat, refLng, parseFloat(d.current_lat), parseFloat(d.current_lng)) }))
        .filter(d => d.distance_km <= 10)
        .sort((a, b) => a.distance_km - b.distance_km)
        .slice(0, limit);

    return withDistance;
}

// Build inline keyboard for driver order offer
function buildOfferKeyboard(orderId) {
    return {
        inline_keyboard: [[
            { text: '✅ Accept Order', callback_data: `accept_order:${orderId}` },
            { text: '❌ Decline', callback_data: `decline_order:${orderId}` }
        ]]
    };
}

// Main entry point — call this after kitchen confirms
async function dispatchOrderToDrivers(order) {
    const refLat = order.location_lat ? parseFloat(order.location_lat) : null;
    const refLng = order.location_lng ? parseFloat(order.location_lng) : null;

    const drivers = await findNearestDrivers(refLat, refLng, 3);

    if (drivers.length === 0) {
        console.log(`[DriverAssignment] No available drivers found for order ${order.order_number}`);
        return;
    }

    console.log(`[DriverAssignment] Dispatching order #${order.order_number} to ${drivers.length} driver(s)`);

    // Import bot lazily to avoid circular dependency
    const TelegramBot = require('node-telegram-bot-api');
    let bot = null;
    if (process.env.DRIVER_BOT_TOKEN) {
        bot = new TelegramBot(process.env.DRIVER_BOT_TOKEN);
    }

    for (const driver of drivers) {
        if (!driver.telegram_user_id) continue;
        try {
            let itemsSummary = '';
            try {
                const items = typeof order.items === 'string' ? JSON.parse(order.items) : order.items;
                if (Array.isArray(items)) {
                    itemsSummary = items.slice(0, 4).map(i => `  • ${i.name} ×${i.quantity}`).join('\n');
                    if (items.length > 4) itemsSummary += `\n  • +${items.length - 4} more`;
                }
            } catch (_) {}

            const distText = driver.distance_km != null
                ? ` (📍 ${driver.distance_km.toFixed(1)} km away)`
                : '';

            const text =
                `🔔 *New Delivery Order!*${distText}\n\n` +
                `📦 Order: *#${order.order_number}*\n` +
                `👤 Customer: ${order.customer_name || 'N/A'}\n` +
                `📞 Phone: ${order.customer_phone || 'N/A'}\n` +
                `📍 Address: ${order.customer_address || 'See order details'}\n` +
                (itemsSummary ? `\n🛒 *Items:*\n${itemsSummary}\n` : '') +
                `\n💰 Total: *${order.total_amount} ETB*\n` +
                `💳 Payment: ${order.payment_method || 'cash'}\n\n` +
                `⚡ First driver to accept gets this order!`;

            if (bot) {
                await bot.sendMessage(driver.telegram_user_id, text, {
                    parse_mode: 'Markdown',
                    reply_markup: buildOfferKeyboard(order.id)
                });
            }

            console.log(`[DriverAssignment] Offer sent to driver ${driver.name} (${driver.telegram_user_id})`);
        } catch (e) {
            console.error(`[DriverAssignment] Failed to notify driver ${driver.name}:`, e.message);
        }
    }
}

// Handle a driver accepting an order — returns { success, alreadyTaken }
async function handleDriverAccept(orderId, driverTelegramId) {
    // Fetch current order state
    const order = await store.findById('orders', orderId);
    if (!order) return { success: false, error: 'Order not found' };

    // If already assigned, tell this driver it's taken
    if (order.driver_id) {
        return { success: false, alreadyTaken: true };
    }

    // Find the driver record
    const driver = await store.findOne('drivers', { telegram_user_id: driverTelegramId });
    if (!driver) return { success: false, error: 'Driver not found' };
    if (!driver.is_approved) return { success: false, error: 'Driver not approved' };

    // Assign driver and update order status
    await store.updateById('orders', orderId, {
        driver_id: driver.id,
        status: 'out_for_delivery'
    });
    await store.updateOne('drivers', { id: driver.id }, { is_available: false });

    const updated = await store.findById('orders', orderId);
    return { success: true, order: updated, driver };
}

module.exports = { dispatchOrderToDrivers, handleDriverAccept, haversineKm };
