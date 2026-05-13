const TelegramBot = require('node-telegram-bot-api');
const store = require('./store');

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

bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const firstName = msg.from.first_name || 'there';
    await bot.sendMessage(chatId,
        `👋 Welcome to *ET-FOOD*, ${firstName}!\n\nOrder delicious food delivered straight to your door. Tap below to browse our menu and place your order.`,
        {
            parse_mode: 'Markdown',
            reply_markup: {
                inline_keyboard: [[
                    { text: '🍔 Open Menu & Order', web_app: { url: WEBAPP_URL } }
                ]]
            }
        }
    );
});

bot.onText(/\/menu/, async (msg) => {
    const chatId = msg.chat.id;
    await bot.sendMessage(chatId, '🍽️ Tap below to browse our full menu:', {
        reply_markup: {
            inline_keyboard: [[
                { text: '📋 View Menu', web_app: { url: WEBAPP_URL } }
            ]]
        }
    });
});

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

bot.onText(/\/help/, async (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId,
        `🤖 *ET-FOOD Bot Commands*\n\n` +
        `/start — Open the food ordering menu\n` +
        `/menu — Browse available dishes\n` +
        `/orders — View your recent orders\n` +
        `/status <order_number> — Check a specific order status\n` +
        `/help — Show this help message`,
        { parse_mode: 'Markdown' }
    );
});

// ===== LIVE LOCATION HANDLING =====

async function saveCustomerLocation(telegramUserId, lat, lng, livePeriod) {
    try {
        const expiresAt = livePeriod
            ? new Date(Date.now() + livePeriod * 1000)
            : new Date(Date.now() + 300 * 1000); // static: keep for 5 min
        const existing = await store.findOne('customer_live_locations', { telegram_user_id: String(telegramUserId) });
        if (existing) {
            await store.updateOne('customer_live_locations',
                { telegram_user_id: String(telegramUserId) },
                { lat, lng, live_period: livePeriod || 0, expires_at: expiresAt, updated_at: new Date() }
            );
        } else {
            const { query } = require('./db');
            await query(
                `INSERT INTO customer_live_locations (telegram_user_id, lat, lng, live_period, expires_at, updated_at)
                 VALUES ($1, $2, $3, $4, $5, NOW())
                 ON CONFLICT (telegram_user_id) DO UPDATE
                 SET lat=$2, lng=$3, live_period=$4, expires_at=$5, updated_at=NOW()`,
                [String(telegramUserId), lat, lng, livePeriod || 0, expiresAt]
            );
        }
    } catch (e) {
        console.error('Error saving customer location:', e.message);
    }
}

// Handle location messages (both one-time and live)
bot.on('message', async (msg) => {
    if (!msg.location) return;
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const { latitude, longitude, live_period } = msg.location;
    await saveCustomerLocation(telegramUserId, latitude, longitude, live_period);

    if (live_period) {
        // Live location
        await bot.sendMessage(chatId,
            `🔴 *Live Location Active!*\n\n` +
            `Your live location is now being tracked and will be used for your deliveries.\n` +
            `📍 Lat: ${latitude.toFixed(5)}, Lng: ${longitude.toFixed(5)}\n\n` +
            `_Location updates automatically while you share it._\n\n` +
            `Tap below to open the menu and order:`,
            {
                parse_mode: 'Markdown',
                reply_markup: {
                    inline_keyboard: [[
                        { text: '🍔 Open Menu & Order', web_app: { url: WEBAPP_URL } }
                    ]]
                }
            }
        );
    } else {
        // One-time location
        await bot.sendMessage(chatId,
            `📍 *Location Saved!*\n\nYour location has been saved for your next order.\n\nTap below to order:`,
            {
                parse_mode: 'Markdown',
                reply_markup: {
                    inline_keyboard: [[
                        { text: '🍔 Open Menu & Order', web_app: { url: WEBAPP_URL } }
                    ]]
                }
            }
        );
    }
});

// Handle live location updates (Telegram sends edited_message when location changes)
bot.on('edited_message', async (msg) => {
    if (!msg.location) return;
    const telegramUserId = String(msg.from.id);
    const { latitude, longitude, live_period } = msg.location;
    await saveCustomerLocation(telegramUserId, latitude, longitude, live_period);
    console.log(`Customer ${telegramUserId} live location updated: ${latitude}, ${longitude}`);
});

// /location command — ask user to share location
bot.onText(/\/location/, async (msg) => {
    const chatId = msg.chat.id;
    await bot.sendMessage(chatId,
        `📍 *Share Your Location*\n\n` +
        `To get faster and more accurate deliveries, share your location:\n\n` +
        `1️⃣ Tap the 📎 (paperclip) button\n` +
        `2️⃣ Choose *Location*\n` +
        `3️⃣ Tap *Share Live Location* for real-time tracking 🔴\n\n` +
        `_Your location is only used for delivery purposes._`,
        { parse_mode: 'Markdown' }
    );
});

bot.on('polling_error', (err) => console.error('Customer bot polling error:', err.message));

module.exports = bot;
