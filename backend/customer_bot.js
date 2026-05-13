const TelegramBot = require('node-telegram-bot-api');
const store = require('./store');
const { query: dbQuery } = require('./db');

const BOT_TOKEN = process.env.BOT_TOKEN;
if (!BOT_TOKEN) { console.error('BOT_TOKEN secret is not set'); process.exit(1); }

const bot = new TelegramBot(BOT_TOKEN, { polling: false });

const WEBAPP_URL = process.env.WEBAPP_URL || `https://${process.env.REPLIT_DEV_DOMAIN || 'localhost:5000'}`;

bot.deleteWebHook({ drop_pending_updates: true }).then(() => {
    bot.startPolling({ restart: false });
    console.log('Customer bot started. WebApp URL:', WEBAPP_URL);
}).catch(err => {
    console.error('Customer bot webhook delete error:', err.message);
    bot.startPolling({ restart: false });
});

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
        if (row.expires_at && new Date(row.expires_at) < new Date()) return null; // expired
        return row;
    } catch (e) {
        console.error('getValidLocation error:', e.message);
        return null;
    }
}

async function saveCustomerLocation(telegramUserId, lat, lng, livePeriod) {
    try {
        // For live locations, keep until live_period ends; for one-time, keep 6 hours
        const expiresAt = livePeriod
            ? new Date(Date.now() + livePeriod * 1000)
            : new Date(Date.now() + 6 * 60 * 60 * 1000);
        await dbQuery(
            `INSERT INTO customer_live_locations (telegram_user_id, lat, lng, live_period, expires_at, updated_at)
             VALUES ($1, $2, $3, $4, $5, NOW())
             ON CONFLICT (telegram_user_id) DO UPDATE
             SET lat=$2, lng=$3, live_period=$4, expires_at=$5, updated_at=NOW()`,
            [String(telegramUserId), lat, lng, livePeriod || 0, expiresAt]
        );
    } catch (e) {
        console.error('Error saving customer location:', e.message);
    }
}

// Inline keyboard with the web app button
function menuKeyboard() {
    return {
        inline_keyboard: [[
            { text: '🍔 Open Menu & Order', web_app: { url: WEBAPP_URL } }
        ]]
    };
}

// Reply keyboard that requests location
function locationRequestKeyboard() {
    return {
        keyboard: [[{ text: '📍 Share My Location', request_location: true }]],
        resize_keyboard: true,
        one_time_keyboard: true
    };
}

// Remove reply keyboard
function removeKeyboard() {
    return { remove_keyboard: true };
}

// ============================================================
// /start — location-gated entry point
// ============================================================

bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const firstName = msg.from.first_name || 'there';

    try {
        const loc = await getValidLocation(telegramUserId);

        if (loc) {
            // User has a valid saved location — show menu directly
            const isLive = loc.live_period > 0;
            const locStatus = isLive
                ? `🔴 Live location active`
                : `📍 Location saved`;

            await bot.sendMessage(chatId,
                `👋 Welcome back, *${firstName}*!\n\n` +
                `${locStatus} — we know where to deliver.\n\n` +
                `Tap below to browse our menu and order:`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: menuKeyboard()
                }
            );
        } else {
            // No valid location — ask for location before showing menu
            await bot.sendMessage(chatId,
                `👋 Welcome to *ET-FOOD*, ${firstName}!\n\n` +
                `🚀 Fresh Ethiopian food delivered to your door.\n\n` +
                `📍 *First, share your location* so we can deliver accurately.\n\n` +
                `Tap the button below 👇\n\n` +
                `_💡 Tip: Choose "Share Live Location" for real-time driver tracking!_`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: locationRequestKeyboard()
                }
            );
        }
    } catch (e) {
        console.error('Error in /start:', e);
        // Fallback — show menu anyway so user is never blocked
        await bot.sendMessage(chatId,
            `👋 Welcome to *ET-FOOD*, ${firstName}!\n\nTap below to order:`,
            { parse_mode: 'Markdown', reply_markup: menuKeyboard() }
        );
    }
});

// ============================================================
// /menu — quick menu shortcut (no location gate)
// ============================================================

bot.onText(/\/menu/, async (msg) => {
    const chatId = msg.chat.id;
    await bot.sendMessage(chatId, '🍽️ Tap below to browse our full menu:', {
        reply_markup: menuKeyboard()
    });
});

// ============================================================
// /orders — view recent orders
// ============================================================

bot.onText(/\/orders/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    try {
        const orders = await store.findMany('orders', { telegram_user_id: telegramUserId }, 'created_at');
        if (!orders.length) {
            return bot.sendMessage(chatId, '📭 You have no orders yet. Use /start to place your first order!');
        }
        const recent = orders.slice(-5).reverse();
        let text = '📦 *Your Recent Orders:*\n\n';
        for (const o of recent) {
            const statusEmoji = {
                pending: '⏳', confirmed: '✅', preparing: '👨‍🍳',
                ready: '🔔', out_for_delivery: '🚗', delivered: '✅', cancelled: '❌'
            }[o.status] || '📦';
            text += `${statusEmoji} *#${o.order_number}*\n`;
            text += `Status: ${o.status.replace(/_/g, ' ')}\n`;
            text += `Total: ${o.total_amount} ETB\n`;
            text += `Date: ${new Date(o.created_at).toLocaleDateString()}\n\n`;
        }
        bot.sendMessage(chatId, text, { parse_mode: 'Markdown' });
    } catch (e) {
        console.error('Error fetching orders:', e);
        bot.sendMessage(chatId, '❌ Failed to fetch orders. Please try again.');
    }
});

// ============================================================
// /status — check specific order
// ============================================================

bot.onText(/\/status (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const orderNumber = match[1].trim().toUpperCase();
    try {
        const orders = await store.findMany('orders', {}, 'created_at');
        const order = orders.find(o => o.order_number === orderNumber || o.order_number === `ET${orderNumber}`);
        if (!order) return bot.sendMessage(chatId, `❌ Order *${orderNumber}* not found.`, { parse_mode: 'Markdown' });
        const statusEmoji = {
            pending: '⏳', confirmed: '✅', preparing: '👨‍🍳',
            ready: '🔔', out_for_delivery: '🚗', delivered: '✅', cancelled: '❌'
        }[order.status] || '📦';
        bot.sendMessage(chatId,
            `📦 *Order ${order.order_number}*\n\n${statusEmoji} Status: *${order.status.replace(/_/g, ' ')}*\nTotal: ${order.total_amount} ETB\nPayment: ${order.payment_method}`,
            { parse_mode: 'Markdown' }
        );
    } catch (e) {
        console.error('Error checking status:', e);
        bot.sendMessage(chatId, '❌ Failed to check order status.');
    }
});

// ============================================================
// /location — prompt user to share/update location
// ============================================================

bot.onText(/\/location/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const loc = await getValidLocation(telegramUserId);

    if (loc) {
        const isLive = loc.live_period > 0;
        const updatedAgo = Math.round((Date.now() - new Date(loc.updated_at)) / 60000);
        await bot.sendMessage(chatId,
            `📍 *Your current location*\n\n` +
            `${isLive ? '🔴 Live location' : '📍 One-time location'}\n` +
            `Updated: ${updatedAgo} min ago\n\n` +
            `To update your location, tap the button below 👇\n\n` +
            `_💡 Tip: Choose "Share Live Location" for real-time driver tracking!_`,
            {
                parse_mode: 'Markdown',
                reply_markup: locationRequestKeyboard()
            }
        );
    } else {
        await bot.sendMessage(chatId,
            `📍 *Share Your Location*\n\n` +
            `Tap the button below to share your location 👇\n\n` +
            `_💡 Choose "Share Live Location" for real-time driver tracking!_`,
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
        `/start — Start ordering (shares your location first)\n` +
        `/menu — Browse available dishes\n` +
        `/location — Update your delivery location\n` +
        `/orders — View your recent orders\n` +
        `/status <order_number> — Check a specific order\n` +
        `/help — Show this help message`,
        { parse_mode: 'Markdown' }
    );
});

// ============================================================
// LOCATION MESSAGES — one-time & live location from keyboard button
// ============================================================

bot.on('message', async (msg) => {
    if (!msg.location) return;

    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const { latitude, longitude, live_period } = msg.location;

    await saveCustomerLocation(telegramUserId, latitude, longitude, live_period);

    if (live_period) {
        // Customer shared a live location — best case!
        await bot.sendMessage(chatId,
            `🔴 *Live Location Active!*\n\n` +
            `Your location is being tracked in real-time.\n` +
            `Drivers will see your exact position as your order is on the way.\n\n` +
            `Tap below to start ordering 🍔`,
            {
                parse_mode: 'Markdown',
                reply_markup: menuKeyboard()
            }
        );
    } else {
        // One-time location — still good, just not live
        await bot.sendMessage(chatId,
            `✅ *Location Saved!*\n\n` +
            `Your delivery location has been set.\n\n` +
            `💡 _Next time, try "Share Live Location" so drivers can track you in real-time!_\n\n` +
            `Tap below to start ordering 🍔`,
            {
                parse_mode: 'Markdown',
                reply_markup: menuKeyboard()
            }
        );
    }
});

// ============================================================
// LIVE LOCATION UPDATES — Telegram sends edited_message when customer moves
// ============================================================

bot.on('edited_message', async (msg) => {
    if (!msg.location) return;
    const telegramUserId = String(msg.from.id);
    const { latitude, longitude, live_period } = msg.location;
    await saveCustomerLocation(telegramUserId, latitude, longitude, live_period);
    console.log(`Live location update — user ${telegramUserId}: ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`);
});

bot.on('polling_error', (err) => console.error('Customer bot polling error:', err.message));

module.exports = bot;
