require('dotenv').config({ path: require('path').join(__dirname, '../.env.example') });

const TelegramBot = require('node-telegram-bot-api');
const store = require('./store');

const BOT_TOKEN = process.env.BOT_TOKEN;
if (!BOT_TOKEN) { console.error('BOT_TOKEN missing in .env.example'); process.exit(1); }

const bot = new TelegramBot(BOT_TOKEN, { polling: true });

const WEBAPP_URL = process.env.WEBAPP_URL || `https://${process.env.REPLIT_DEV_DOMAIN || 'localhost:5000'}`;

console.log('Customer bot started. WebApp URL:', WEBAPP_URL);

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

bot.on('polling_error', (err) => console.error('Customer bot polling error:', err.message));

module.exports = bot;
