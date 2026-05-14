const TelegramBot = require('node-telegram-bot-api');
const store = require('./store');
const { query: dbQuery } = require('./db');

const BOT_TOKEN = process.env.BOT_TOKEN;
if (!BOT_TOKEN) { console.error('BOT_TOKEN secret is not set'); process.exit(1); }

const bot = new TelegramBot(BOT_TOKEN, { polling: false });

const WEBAPP_URL = process.env.WEBAPP_URL || `https://${process.env.REPLIT_DEV_DOMAIN || 'localhost:5000'}`;

bot.deleteWebHook({ drop_pending_updates: true }).then(() => {
    bot.startPolling({
        restart: false,
        params: {
            allowed_updates: ['message', 'edited_message', 'callback_query']
        }
    });
    console.log('Customer bot started. WebApp URL:', WEBAPP_URL);
}).catch(err => {
    console.error('Customer bot webhook delete error:', err.message);
    bot.startPolling({
        restart: false,
        params: {
            allowed_updates: ['message', 'edited_message', 'callback_query']
        }
    });
});

// ============================================================
// CUSTOMER PROFILE HELPERS
// ============================================================

const customerSessions = {};

function getCustSession(userId) {
    if (!customerSessions[userId]) customerSessions[userId] = { step: null };
    return customerSessions[userId];
}

async function getCustomerProfile(telegramUserId) {
    try {
        const result = await dbQuery('SELECT * FROM customers WHERE telegram_user_id = $1', [String(telegramUserId)]);
        return result.rows[0] || null;
    } catch (e) {
        console.error('getCustomerProfile error:', e.message);
        return null;
    }
}

async function saveCustomerProfile(telegramUserId, name, phoneNumber) {
    await dbQuery(
        `INSERT INTO customers (telegram_user_id, name, phone_number, updated_at)
         VALUES ($1, $2, $3, NOW())
         ON CONFLICT (telegram_user_id) DO UPDATE SET name=$2, phone_number=$3, updated_at=NOW()`,
        [String(telegramUserId), name, phoneNumber]
    );
}

// ============================================================
// HELPERS
// ============================================================

async function getValidLocation(telegramUserId) {
    try {
        const result = await dbQuery(
            `SELECT * FROM customer_live_locations WHERE telegram_user_id = $1`,
            [String(telegramUserId)]
        );
        const row = result.rows[0];
        if (!row) return null;
        // For live locations, never expire them prematurely — keep until Telegram stops sending updates
        if (row.live_period > 0) return row; // live location — always valid while active
        if (row.expires_at && new Date(row.expires_at) < new Date()) return null; // static expired
        return row;
    } catch (e) {
        console.error('getValidLocation error:', e.message);
        return null;
    }
}

async function saveCustomerLocation(telegramUserId, lat, lng, livePeriod) {
    try {
        // live location: keep 8 hours from last update (Telegram max live period is 8h)
        // static location: keep 6 hours
        const expiresAt = livePeriod
            ? new Date(Date.now() + 8 * 60 * 60 * 1000)
            : new Date(Date.now() + 6 * 60 * 60 * 1000);
        await dbQuery(
            `INSERT INTO customer_live_locations (telegram_user_id, lat, lng, live_period, expires_at, updated_at)
             VALUES ($1, $2, $3, $4, $5, NOW())
             ON CONFLICT (telegram_user_id) DO UPDATE
             SET lat=$2, lng=$3, live_period=$4, expires_at=$5, updated_at=NOW()`,
            [String(telegramUserId), lat, lng, livePeriod || 0, expiresAt]
        );
        // Also update any active orders with this customer's latest location
        await dbQuery(
            `UPDATE orders SET location_lat=$2, location_lng=$3, updated_at=NOW()
             WHERE telegram_user_id=$1 AND status NOT IN ('delivered','cancelled')`,
            [String(telegramUserId), lat, lng]
        );
    } catch (e) {
        console.error('Error saving customer location:', e.message);
    }
}

// Persistent reply keyboard shown after location is set
function mainKeyboard() {
    return {
        keyboard: [
            [{ text: '🍔 Order Food' }, { text: '📦 My Orders' }],
            [{ text: '📍 Update Location' }, { text: '🆘 Help' }]
        ],
        resize_keyboard: true,
        persistent: true
    };
}

// Inline keyboard with the web app button (embed user ID in URL for reliable autofill)
function menuKeyboard(telegramUserId) {
    const url = telegramUserId ? `${WEBAPP_URL}?uid=${telegramUserId}` : WEBAPP_URL;
    return {
        inline_keyboard: [[
            { text: '🍔 Open Menu & Order', web_app: { url } }
        ]]
    };
}

// Reply keyboard that requests location
function locationRequestKeyboard() {
    return {
        keyboard: [
            [{ text: '📍 Send My Current Location', request_location: true }],
            [{ text: '🔴 Share Live Location (Recommended)', request_location: true }]
        ],
        resize_keyboard: true,
        one_time_keyboard: true
    };
}

const STATUS_EMOJI = {
    pending: '⏳',
    confirmed: '✅',
    kitchen_confirmed: '👨‍🍳',
    preparing: '👨‍🍳',
    ready: '🔔',
    out_for_delivery: '🚗',
    delivered: '✅',
    cancelled: '❌'
};

const STATUS_LABEL = {
    pending: 'Pending',
    confirmed: 'Confirmed',
    kitchen_confirmed: 'Preparing',
    preparing: 'Preparing',
    ready: 'Ready for Pickup',
    out_for_delivery: 'On the Way',
    delivered: 'Delivered',
    cancelled: 'Cancelled'
};

const ACTIVE_STATUSES = ['pending', 'confirmed', 'kitchen_confirmed', 'preparing', 'ready', 'out_for_delivery'];
const DONE_STATUSES = ['delivered', 'cancelled'];

// ============================================================
// ORDERS PANEL HELPERS
// ============================================================

async function getCustomerOrders(telegramUserId) {
    try {
        const result = await dbQuery(
            `SELECT * FROM orders WHERE telegram_user_id=$1 ORDER BY created_at DESC LIMIT 30`,
            [String(telegramUserId)]
        );
        return result.rows;
    } catch (e) {
        console.error('getCustomerOrders error:', e.message);
        return [];
    }
}

async function sendOrdersPanel(chatId, telegramUserId, tab = 'active') {
    const orders = await getCustomerOrders(telegramUserId);
    const activeOrders = orders.filter(o => ACTIVE_STATUSES.includes(o.status));
    const doneOrders = orders.filter(o => DONE_STATUSES.includes(o.status));

    const list = tab === 'active' ? activeOrders : doneOrders;
    const tabLabel = tab === 'active' ? 'Active Orders' : 'Order History';

    let text = `📦 *${tabLabel}*\n`;
    text += `Active: ${activeOrders.length}  |  History: ${doneOrders.length}\n\n`;

    if (list.length === 0) {
        text += tab === 'active'
            ? '✅ No active orders right now.\n\nTap 🍔 *Order Food* to place a new order!'
            : '📭 No completed orders yet.';
    } else {
        for (const o of list.slice(0, 8)) {
            const emoji = STATUS_EMOJI[o.status] || '📦';
            const label = STATUS_LABEL[o.status] || o.status;
            const date = new Date(o.created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
            text += `${emoji} *#${o.order_number}* — ${label}\n`;
            text += `   ${o.total_amount} ETB · ${date}\n`;
        }
        if (list.length > 8) text += `\n_...and ${list.length - 8} more_`;
    }

    const tabButtons = [
        { text: tab === 'active' ? '🟢 Active Orders ✓' : '🟢 Active Orders', callback_data: 'orders:active' },
        { text: tab === 'done' ? '📋 History ✓' : '📋 History', callback_data: 'orders:done' }
    ];

    const orderButtons = list.slice(0, 6).map(o => ([{
        text: `${STATUS_EMOJI[o.status] || '📦'} #${o.order_number} — ${STATUS_LABEL[o.status] || o.status}`,
        callback_data: `order:${o.id}`
    }]));

    const bottomRow = [[{ text: '🍔 New Order', web_app: { url: `${WEBAPP_URL}?uid=${telegramUserId}` } }]];

    return bot.sendMessage(chatId, text, {
        parse_mode: 'Markdown',
        reply_markup: {
            inline_keyboard: [tabButtons, ...orderButtons, ...bottomRow]
        }
    });
}

async function sendOrderDetail(chatId, orderId) {
    try {
        const result = await dbQuery(`SELECT * FROM orders WHERE id=$1`, [orderId]);
        const o = result.rows[0];
        if (!o) return bot.sendMessage(chatId, '❌ Order not found.');

        const emoji = STATUS_EMOJI[o.status] || '📦';
        const label = STATUS_LABEL[o.status] || o.status;
        const date = new Date(o.created_at).toLocaleString('en-GB', {
            day: '2-digit', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });

        let items = '';
        try {
            const parsed = typeof o.items === 'string' ? JSON.parse(o.items) : o.items;
            if (Array.isArray(parsed)) {
                items = parsed.map(i => `  • ${i.name} x${i.quantity} — ${i.price * i.quantity} ETB`).join('\n');
            }
        } catch (_) {}

        let text = `📦 *Order #${o.order_number}*\n`;
        text += `${emoji} Status: *${label}*\n\n`;
        if (items) text += `🛒 *Items:*\n${items}\n\n`;
        text += `💰 Total: *${o.total_amount} ETB*\n`;
        text += `💳 Payment: ${o.payment_method || 'N/A'} (${o.payment_status || 'pending'})\n`;
        text += `📅 Placed: ${date}\n`;
        if (o.special_instructions) text += `📝 Notes: ${o.special_instructions}\n`;

        let driver = null;
        if (o.driver_id) {
            const dr = await dbQuery(`SELECT * FROM drivers WHERE id=$1`, [o.driver_id]);
            if (dr.rows[0]) driver = dr.rows[0];
        }
        if (driver) {
            text += `\n🚗 *Driver:* ${driver.name}\n📞 ${driver.phone_number}`;
        }

        const backButton = [[{ text: '⬅️ Back to Orders', callback_data: 'orders:active' }]];

        return bot.sendMessage(chatId, text, {
            parse_mode: 'Markdown',
            reply_markup: { inline_keyboard: backButton }
        });
    } catch (e) {
        console.error('sendOrderDetail error:', e.message);
        return bot.sendMessage(chatId, '❌ Failed to load order details.');
    }
}

// ============================================================
// /start — location-gated entry point
// ============================================================

bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const firstName = msg.from.first_name || 'there';
    const session = getCustSession(telegramUserId);

    try {
        // Check if customer profile already exists
        const profile = await getCustomerProfile(telegramUserId);

        if (!profile) {
            // New customer — collect phone number first
            session.step = 'await_phone';
            session.firstName = firstName;
            return bot.sendMessage(chatId,
                `👋 Welcome to *ET-FOOD*, ${firstName}!\n\n` +
                `🚀 Fresh Ethiopian food delivered to your door.\n\n` +
                `📱 *Step 1:* Please share your phone number so we can contact you about your orders:`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: {
                        keyboard: [[{ text: '📱 Share My Phone Number', request_contact: true }]],
                        resize_keyboard: true,
                        one_time_keyboard: true
                    }
                }
            );
        }

        // Existing customer — clear any stale session and go straight to location/menu
        session.step = null;
        const loc = await getValidLocation(telegramUserId);
        const displayName = profile.name || firstName;

        if (loc) {
            const isLive = loc.live_period > 0;
            const locStatus = isLive ? '🔴 Live location active' : '📍 Location saved';
            await bot.sendMessage(chatId,
                `👋 Welcome back, *${displayName}*!\n\n${locStatus} — we know where to deliver.\n\nTap below to browse our menu and order:`,
                { parse_mode: 'Markdown', reply_markup: mainKeyboard() }
            );
            await bot.sendMessage(chatId, '🍔 Ready to order?', { reply_markup: menuKeyboard(telegramUserId) });
        } else {
            await bot.sendMessage(chatId,
                `👋 Welcome back, *${displayName}*!\n\n` +
                `📍 *Share your location* so we can deliver accurately.\n\n` +
                `💡 *Tip: Choose "Share Live Location"* for real-time tracking!`,
                { parse_mode: 'Markdown', reply_markup: locationRequestKeyboard() }
            );
        }
    } catch (e) {
        console.error('Error in /start:', e);
        await bot.sendMessage(chatId,
            `👋 Welcome to *ET-FOOD*, ${firstName}!\n\nTap below to order:`,
            { parse_mode: 'Markdown', reply_markup: menuKeyboard(telegramUserId) }
        );
    }
});

// ============================================================
// /menu
// ============================================================

bot.onText(/\/menu/, async (msg) => {
    const chatId = msg.chat.id;
    const uid = String(msg.from.id);
    await bot.sendMessage(chatId, '🍽️ Tap below to browse our full menu:', {
        reply_markup: menuKeyboard(uid)
    });
});

// ============================================================
// /orders
// ============================================================

bot.onText(/\/orders/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    await sendOrdersPanel(chatId, telegramUserId, 'active');
});

// ============================================================
// /status <order_number>
// ============================================================

bot.onText(/\/status (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const orderNumber = match[1].trim().toUpperCase();
    try {
        const result = await dbQuery(
            `SELECT * FROM orders WHERE order_number=$1 OR order_number=$2`,
            [orderNumber, `ET${orderNumber}`]
        );
        const order = result.rows[0];
        if (!order) return bot.sendMessage(chatId, `❌ Order *${orderNumber}* not found.`, { parse_mode: 'Markdown' });
        const emoji = STATUS_EMOJI[order.status] || '📦';
        const label = STATUS_LABEL[order.status] || order.status;
        bot.sendMessage(chatId,
            `📦 *Order ${order.order_number}*\n\n${emoji} Status: *${label}*\nTotal: ${order.total_amount} ETB\nPayment: ${order.payment_method}`,
            { parse_mode: 'Markdown' }
        );
    } catch (e) {
        console.error('Error checking status:', e);
        bot.sendMessage(chatId, '❌ Failed to check order status.');
    }
});

// ============================================================
// /location — prompt user to update location
// ============================================================

bot.onText(/\/location/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const loc = await getValidLocation(telegramUserId);

    if (loc) {
        const isLive = loc.live_period > 0;
        const updatedAgo = Math.round((Date.now() - new Date(loc.updated_at)) / 60000);
        await bot.sendMessage(chatId,
            `📍 *Your Current Location*\n\n` +
            `${isLive ? '🔴 Live location — updating in real-time' : '📍 Static location'}\n` +
            `Last updated: ${updatedAgo} min ago\n\n` +
            `To update, share your location again below:\n\n` +
            `💡 *Choose "Share Live Location"* so your driver always knows where you are!`,
            {
                parse_mode: 'Markdown',
                reply_markup: locationRequestKeyboard()
            }
        );
    } else {
        await bot.sendMessage(chatId,
            `📍 *Share Your Location*\n\n` +
            `Tap below to share your location 👇\n\n` +
            `💡 *Choose "Share Live Location"* — updates automatically as you move!`,
            {
                parse_mode: 'Markdown',
                reply_markup: locationRequestKeyboard()
            }
        );
    }
});

// ============================================================
// /help
// ============================================================

bot.onText(/\/help/, async (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId,
        `🤖 *ET-FOOD Bot Commands*\n\n` +
        `🍔 *Order Food* — Browse menu and order\n` +
        `📦 *My Orders* — View active & completed orders\n` +
        `📍 *Update Location* — Change delivery location\n\n` +
        `/start — Welcome screen\n` +
        `/menu — Open menu\n` +
        `/orders — View orders\n` +
        `/location — Update location\n` +
        `/status <order#> — Check specific order\n` +
        `/help — This help message\n\n` +
        `📞 *For support*, contact the restaurant directly.`,
        { parse_mode: 'Markdown' }
    );
});

// ============================================================
// REPLY KEYBOARD BUTTON HANDLERS
// ============================================================

bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const session = getCustSession(telegramUserId);

    // ── Handle phone number sharing (contact) ──────────────────
    if (msg.contact) {
        if (session.step === 'await_phone') {
            const phone = msg.contact.phone_number;
            session.phone = phone;
            session.step = 'await_name';
            return bot.sendMessage(chatId,
                `✅ Phone number saved!\n\n👤 *Step 2:* Please enter your *full name*:`,
                { parse_mode: 'Markdown', reply_markup: { remove_keyboard: true } }
            );
        }
        return;
    }

    // ── Handle name collection ─────────────────────────────────
    if (session.step === 'await_name') {
        const text = msg.text || '';
        if (text.length < 2) {
            return bot.sendMessage(chatId, '⚠️ Please enter your full name (at least 2 characters).');
        }
        const name = text.trim();
        try {
            await saveCustomerProfile(telegramUserId, name, session.phone || null);
            session.step = null;
            const profile = { name, phone_number: session.phone };
            session.phone = null;

            await bot.sendMessage(chatId,
                `🎉 *Profile saved!*\n\nName: *${name}*\nPhone: ${profile.phone_number || 'N/A'}\n\n` +
                `📍 Now, share your location so we can deliver to you:`,
                { parse_mode: 'Markdown', reply_markup: locationRequestKeyboard() }
            );
        } catch (e) {
            console.error('Profile save error:', e.message);
            bot.sendMessage(chatId, '❌ Failed to save profile. Please try /start again.');
        }
        return;
    }

    // Handle location messages (both static and initial live location)
    if (msg.location) {
        const { latitude, longitude, live_period } = msg.location;

        await saveCustomerLocation(telegramUserId, latitude, longitude, live_period);

        if (live_period) {
            await bot.sendMessage(chatId,
                `🔴 *Live Location Active!*\n\n` +
                `Your location updates automatically as you move.\n` +
                `Your driver will always see your exact position.\n\n` +
                `Use the buttons below to order 🍔`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: mainKeyboard()
                }
            );
            await bot.sendMessage(chatId, '🍔 Ready to order?', { reply_markup: menuKeyboard(telegramUserId) });
        } else {
            await bot.sendMessage(chatId,
                `✅ *Location Saved!*\n\n` +
                `Your delivery location has been set.\n\n` +
                `💡 _Next time, try "Share Live Location" so your driver can track you in real-time!_`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: mainKeyboard()
                }
            );
            await bot.sendMessage(chatId, '🍔 Ready to order?', { reply_markup: menuKeyboard(telegramUserId) });
        }
        return;
    }

    const text = msg.text || '';

    if (text.startsWith('/')) return;

    if (text === '🍔 Order Food') {
        return bot.sendMessage(chatId, '🍔 Tap below to browse our full menu and order:', {
            reply_markup: menuKeyboard(telegramUserId)
        });
    }

    if (text === '📦 My Orders') {
        return sendOrdersPanel(chatId, telegramUserId, 'active');
    }

    if (text === '📍 Update Location') {
        return bot.sendMessage(chatId,
            `📍 *Update Your Delivery Location*\n\n` +
            `Tap the button below 👇\n\n` +
            `💡 *Choose "Share Live Location"* — updates automatically as you move!`,
            {
                parse_mode: 'Markdown',
                reply_markup: locationRequestKeyboard()
            }
        );
    }

    if (text === '🆘 Help') {
        return bot.sendMessage(chatId,
            `🤖 *ET-FOOD Help*\n\n` +
            `🍔 *Order Food* — Browse menu and order\n` +
            `📦 *My Orders* — View active & completed orders\n` +
            `📍 *Update Location* — Change delivery address\n\n` +
            `Commands: /start /menu /orders /location /help`,
            { parse_mode: 'Markdown' }
        );
    }
});

// ============================================================
// LIVE LOCATION UPDATES — Telegram sends edited_message when customer moves
// This is the correct Telegram API approach for real-time location tracking
// ============================================================

bot.on('edited_message', async (msg) => {
    if (!msg.location) return;
    const telegramUserId = String(msg.from.id);
    const { latitude, longitude, live_period } = msg.location;

    // Save the updated live location — this is what keeps the driver's view current
    await saveCustomerLocation(telegramUserId, latitude, longitude, live_period);
    console.log(`📍 Live location update — customer ${telegramUserId}: ${latitude.toFixed(5)}, ${longitude.toFixed(5)}${live_period ? ` (live, ${live_period}s)` : ' (static updated)'}`);
});

// ============================================================
// CALLBACK QUERIES — Orders panel navigation
// ============================================================

bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const telegramUserId = String(query.from.id);
    const data = query.data;

    try {
        await bot.answerCallbackQuery(query.id);

        if (data === 'orders:active' || data === 'orders:done') {
            const tab = data === 'orders:active' ? 'active' : 'done';
            try {
                await bot.deleteMessage(chatId, query.message.message_id);
            } catch (_) {}
            return sendOrdersPanel(chatId, telegramUserId, tab);
        }

        if (data.startsWith('order:')) {
            const orderId = data.replace('order:', '');
            try {
                await bot.deleteMessage(chatId, query.message.message_id);
            } catch (_) {}
            return sendOrderDetail(chatId, orderId);
        }

        if (data.startsWith('confirm_delivery:')) {
            const orderId = data.replace('confirm_delivery:', '');
            try {
                const result = await dbQuery(`SELECT * FROM orders WHERE id=$1`, [orderId]);
                const order = result.rows[0];
                if (!order) return bot.sendMessage(chatId, '❌ Order not found.');

                // Remove the confirmation buttons
                try {
                    await bot.editMessageReplyMarkup({ inline_keyboard: [] }, {
                        chat_id: chatId, message_id: query.message.message_id
                    });
                } catch (_) {}

                // Mark order as customer-confirmed in DB
                await dbQuery(`UPDATE orders SET payment_status='confirmed' WHERE id=$1`, [orderId]).catch(() => {});

                // Show thank-you + ask driver rating
                await bot.sendMessage(chatId,
                    `🎉 *Delivery Confirmed! #${order.order_number}*\n\n` +
                    `Thank you! We hope you enjoy your meal. 🍽️\n\n` +
                    `Please rate your driver:`,
                    {
                        parse_mode: 'Markdown',
                        reply_markup: {
                            inline_keyboard: [[
                                { text: '⭐', callback_data: `rate_driver:${orderId}:1` },
                                { text: '⭐⭐', callback_data: `rate_driver:${orderId}:2` },
                                { text: '⭐⭐⭐', callback_data: `rate_driver:${orderId}:3` },
                                { text: '⭐⭐⭐⭐', callback_data: `rate_driver:${orderId}:4` },
                                { text: '⭐⭐⭐⭐⭐', callback_data: `rate_driver:${orderId}:5` }
                            ]]
                        }
                    }
                );
            } catch (e) {
                console.error('confirm_delivery error:', e.message);
                bot.sendMessage(chatId, '❌ Failed to confirm delivery. Please try again.');
            }
            return;
        }

        if (data.startsWith('rate_driver:')) {
            const parts = data.split(':');
            const orderId = parts[1];
            const stars = parseInt(parts[2]);
            try {
                // Remove rating buttons
                try {
                    await bot.editMessageReplyMarkup({ inline_keyboard: [] }, {
                        chat_id: chatId, message_id: query.message.message_id
                    });
                } catch (_) {}

                // Save driver rating
                const result = await dbQuery(`SELECT * FROM orders WHERE id=$1`, [orderId]);
                const order = result.rows[0];
                if (order && order.driver_id) {
                    // Weighted average: new_rating = (old_rating * deliveries + stars) / (deliveries + 1)
                    await dbQuery(
                        `UPDATE drivers
                         SET rating = ROUND((rating * total_deliveries + $1) / (total_deliveries + 1), 1),
                             total_deliveries = total_deliveries + 1
                         WHERE id = $2`,
                        [stars, order.driver_id]
                    ).catch(e => console.error('driver rating save error:', e.message));
                }

                const starDisplay = '⭐'.repeat(stars);
                await bot.sendMessage(chatId,
                    `${starDisplay} *Driver rated ${stars}/5 — Thank you!*\n\nNow please rate the restaurant:`,
                    {
                        parse_mode: 'Markdown',
                        reply_markup: {
                            inline_keyboard: [[
                                { text: '⭐', callback_data: `rate_restaurant:${orderId}:1` },
                                { text: '⭐⭐', callback_data: `rate_restaurant:${orderId}:2` },
                                { text: '⭐⭐⭐', callback_data: `rate_restaurant:${orderId}:3` },
                                { text: '⭐⭐⭐⭐', callback_data: `rate_restaurant:${orderId}:4` },
                                { text: '⭐⭐⭐⭐⭐', callback_data: `rate_restaurant:${orderId}:5` }
                            ]]
                        }
                    }
                );
            } catch (e) {
                console.error('rate_driver error:', e.message);
            }
            return;
        }

        if (data.startsWith('rate_restaurant:')) {
            const parts = data.split(':');
            const orderId = parts[1];
            const stars = parseInt(parts[2]);
            try {
                // Remove rating buttons
                try {
                    await bot.editMessageReplyMarkup({ inline_keyboard: [] }, {
                        chat_id: chatId, message_id: query.message.message_id
                    });
                } catch (_) {}

                // Save restaurant rating
                const result = await dbQuery(`SELECT * FROM orders WHERE id=$1`, [orderId]);
                const order = result.rows[0];
                if (order && order.restaurant_id) {
                    await dbQuery(
                        `UPDATE restaurants
                         SET rating = ROUND(
                             (COALESCE(rating, 5.0) * COALESCE(rating_count, 0) + $1) /
                             (COALESCE(rating_count, 0) + 1), 1),
                             rating_count = COALESCE(rating_count, 0) + 1
                         WHERE id = $2`,
                        [stars, order.restaurant_id]
                    ).catch(e => console.error('restaurant rating save error:', e.message));
                }

                const starDisplay = '⭐'.repeat(stars);
                await bot.sendMessage(chatId,
                    `${starDisplay} *Restaurant rated ${stars}/5 — Thank you!*\n\n` +
                    `Your feedback helps us serve you better. 🙏\n\n` +
                    `Come back soon to ET-FOOD!`,
                    {
                        parse_mode: 'Markdown',
                        reply_markup: {
                            inline_keyboard: [[
                                { text: '🍔 Order Again', web_app: { url: `${WEBAPP_URL}?uid=${telegramUserId}` } }
                            ]]
                        }
                    }
                );
            } catch (e) {
                console.error('rate_restaurant error:', e.message);
            }
            return;
        }

    } catch (e) {
        console.error('Callback query error:', e.message);
    }
});

bot.on('polling_error', (err) => console.error('Customer bot polling error:', err.message));

module.exports = bot;
