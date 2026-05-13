const TelegramBot = require('node-telegram-bot-api');
const store = require('./store');

const DRIVER_BOT_TOKEN = process.env.DRIVER_BOT_TOKEN;
if (!DRIVER_BOT_TOKEN) { console.error('DRIVER_BOT_TOKEN secret is not set'); process.exit(1); }

const bot = new TelegramBot(DRIVER_BOT_TOKEN, { polling: true });

console.log('Driver bot started.');

const driverSessions = {};

function getSession(userId) {
    if (!driverSessions[userId]) driverSessions[userId] = { step: null, data: {} };
    return driverSessions[userId];
}

async function getDriver(telegramUserId) {
    return store.findOne('drivers', { telegram_user_id: String(telegramUserId) });
}

function getWebAppUrl(telegramUserId) {
    const base = process.env.WEBAPP_URL ||
        (process.env.REPLIT_DEV_DOMAIN ? `https://${process.env.REPLIT_DEV_DOMAIN}` : '');
    return `${base}/driver-panel?driver_id=${telegramUserId}`;
}

async function sendMainMenu(chatId, driver, telegramUserId) {
    const statusText = driver.is_available ? '🟢 Online' : '🔴 Offline';
    const approvedText = driver.is_approved ? '✅ Approved' : '⏳ Pending Approval';
    const webAppUrl = getWebAppUrl(telegramUserId || driver.telegram_user_id);

    await bot.sendMessage(chatId,
        `🚗 *Driver Panel*\n\n👤 Name: ${driver.name}\n📊 Status: ${statusText}\n🏷️ Account: ${approvedText}\n\nUse the *Driver WebApp* to manage orders, track GPS, and upload documents.`,
        {
            parse_mode: 'Markdown',
            reply_markup: {
                inline_keyboard: [
                    [{ text: '🗂️ Open Driver Panel', web_app: { url: webAppUrl } }],
                    [
                        { text: driver.is_available ? '🔴 Go Offline' : '🟢 Go Online', callback_data: driver.is_available ? 'go_offline' : 'go_online' },
                        { text: '📊 My Stats', callback_data: 'my_stats' }
                    ],
                    [
                        { text: '📦 My Orders', callback_data: 'my_orders' },
                        { text: '📁 Upload Docs', callback_data: 'upload_docs' }
                    ]
                ]
            }
        }
    );

    // Also show location keyboard
    await bot.sendMessage(chatId, '📍 Tap below to share your live location:', {
        reply_markup: {
            keyboard: [
                [{ text: '📍 Share My Location', request_location: true }],
                [{ text: '🆘 Help' }]
            ],
            resize_keyboard: true
        }
    });
}

bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const session = getSession(telegramUserId);

    try {
        const existing = await getDriver(telegramUserId);
        if (existing) {
            await bot.sendMessage(chatId, `👋 Welcome back, *${existing.name}*!`, { parse_mode: 'Markdown' });
            return sendMainMenu(chatId, existing, telegramUserId);
        }

        session.step = 'register_name';
        session.data = {};
        bot.sendMessage(chatId,
            `👋 Welcome to *ET-FOOD Driver Bot*!\n\nTo get started, I need a few details. You'll be verified by our team before you can accept deliveries.\n\n📝 *Step 1/3:* Please enter your *full name*:`,
            { parse_mode: 'Markdown', reply_markup: { remove_keyboard: true } }
        );
    } catch (e) {
        console.error('Start error:', e);
        bot.sendMessage(chatId, '❌ An error occurred. Please try again.');
    }
});

bot.onText(/\/panel/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    try {
        const driver = await getDriver(telegramUserId);
        if (!driver) return bot.sendMessage(chatId, '❌ You are not registered. Use /start to register.');
        const webAppUrl = getWebAppUrl(telegramUserId);
        bot.sendMessage(chatId, '🗂️ Open your Driver Panel:', {
            reply_markup: {
                inline_keyboard: [[{ text: '🚗 Open Driver Panel', web_app: { url: webAppUrl } }]]
            }
        });
    } catch (e) {
        console.error(e);
    }
});

bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const telegramUserId = String(query.from.id);
    const data = query.data;

    try {
        const driver = await getDriver(telegramUserId);
        if (!driver) {
            bot.answerCallbackQuery(query.id, { text: 'You are not registered.' });
            return;
        }

        if (data === 'go_online' || data === 'go_offline') {
            const goOnline = data === 'go_online';
            if (!driver.is_approved && goOnline) {
                bot.answerCallbackQuery(query.id, { text: '⏳ Your account is still pending approval.', show_alert: true });
                return;
            }
            await store.updateOne('drivers', { telegram_user_id: telegramUserId }, { is_available: goOnline });
            bot.answerCallbackQuery(query.id, { text: goOnline ? '🟢 You are now Online!' : '🔴 You are now Offline.' });
            const updated = await getDriver(telegramUserId);
            return sendMainMenu(chatId, updated, telegramUserId);
        }

        if (data === 'my_stats') {
            bot.answerCallbackQuery(query.id);
            bot.sendMessage(chatId,
                `📊 *Your Statistics*\n\n🚚 Total Deliveries: ${driver.total_deliveries || 0}\n⭐ Rating: ${driver.rating || 5.0}\n📊 Status: ${driver.is_available ? 'Online' : 'Offline'}\n✅ Account: ${driver.is_approved ? 'Approved' : 'Pending'}`,
                { parse_mode: 'Markdown' }
            );
            return;
        }

        if (data === 'my_orders') {
            bot.answerCallbackQuery(query.id);
            const orders = await store.findMany('orders', {}, 'created_at');
            const myOrders = orders.filter(o => o.driver_id === driver.id && o.status === 'out_for_delivery');
            if (!myOrders.length) {
                return bot.sendMessage(chatId, '📭 No active deliveries right now.');
            }
            for (const o of myOrders) {
                const webAppUrl = getWebAppUrl(telegramUserId) + `&order_id=${o.id}`;
                bot.sendMessage(chatId,
                    `🚗 *Active Delivery*\n\nOrder: #${o.order_number}\nCustomer: ${o.customer_name}\nPhone: ${o.customer_phone}\nAddress: ${o.customer_address || 'Not provided'}\nTotal: ${o.total_amount} ETB`,
                    {
                        parse_mode: 'Markdown',
                        reply_markup: {
                            inline_keyboard: [[{ text: '🗺️ View Order on Map', web_app: { url: webAppUrl } }]]
                        }
                    }
                );
            }
            return;
        }

        if (data === 'upload_docs') {
            bot.answerCallbackQuery(query.id);
            const webAppUrl = getWebAppUrl(telegramUserId) + '&section=documents';
            bot.sendMessage(chatId,
                `📁 *Upload Documents*\n\nYou can upload your required documents (ID, driver\'s license, vehicle registration) via the Driver Panel.`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: {
                        inline_keyboard: [[{ text: '📁 Open Document Upload', web_app: { url: webAppUrl } }]]
                    }
                }
            );
            return;
        }

    } catch (e) {
        console.error('Callback query error:', e);
        bot.answerCallbackQuery(query.id, { text: 'An error occurred.' });
    }
});

bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const text = msg.text || '';
    const session = getSession(telegramUserId);

    if (msg.location) {
        try {
            const driver = await getDriver(telegramUserId);
            if (!driver) return bot.sendMessage(chatId, '❌ You are not registered. Use /start to register.');
            await store.updateOne('drivers', { telegram_user_id: telegramUserId }, {
                current_lat: msg.location.latitude,
                current_lng: msg.location.longitude,
                last_location_update: new Date()
            });
            bot.sendMessage(chatId, '📍 Location updated successfully! ✅');
        } catch (e) {
            console.error('Location update error:', e);
        }
        return;
    }

    if (text.startsWith('/')) return;

    if (session.step === 'register_name') {
        if (text.length < 2) return bot.sendMessage(chatId, '⚠️ Please enter a valid full name (at least 2 characters).');
        session.data.name = text.trim();
        session.step = 'register_phone';
        return bot.sendMessage(chatId, `✅ Name saved: *${session.data.name}*\n\n📞 *Step 2/3:* Enter your *phone number* (e.g. +251911234567):`, { parse_mode: 'Markdown' });
    }

    if (session.step === 'register_phone') {
        if (text.length < 7) return bot.sendMessage(chatId, '⚠️ Please enter a valid phone number.');
        session.data.phone_number = text.trim();
        session.step = 'register_vehicle';
        return bot.sendMessage(chatId,
            `✅ Phone saved.\n\n🚗 *Step 3/3:* Select your *vehicle type*:`,
            {
                parse_mode: 'Markdown',
                reply_markup: {
                    keyboard: [
                        [{ text: '🏍️ Motorcycle' }, { text: '🚗 Car' }],
                        [{ text: '🚲 Bicycle' }, { text: '🛵 Scooter' }]
                    ],
                    resize_keyboard: true, one_time_keyboard: true
                }
            }
        );
    }

    if (session.step === 'register_vehicle') {
        const vehicleMap = { '🏍️ Motorcycle': 'motorcycle', '🚗 Car': 'car', '🚲 Bicycle': 'bicycle', '🛵 Scooter': 'scooter' };
        const vehicle = vehicleMap[text] || text.toLowerCase();
        session.data.vehicle_type = vehicle;
        session.step = null;

        try {
            await store.insertOne('drivers', {
                name: session.data.name,
                phone_number: session.data.phone_number,
                telegram_user_id: telegramUserId,
                vehicle_type: vehicle,
                is_active: true,
                is_available: false,
                is_approved: false,
                total_deliveries: 0,
                rating: 5.0
            });
            bot.sendMessage(chatId,
                `🎉 *Registration Complete!*\n\nName: ${session.data.name}\nPhone: ${session.data.phone_number}\nVehicle: ${vehicle}\n\n⏳ Your account is now *pending approval* by our team. You will be notified once approved!\n\nUse /start anytime to check your status.`,
                { parse_mode: 'Markdown', reply_markup: { remove_keyboard: true } }
            );
        } catch (e) {
            console.error('Registration error:', e);
            bot.sendMessage(chatId, '❌ Registration failed. Please try /start again.');
        }
        return;
    }

    if (text === '🆘 Help') {
        bot.sendMessage(chatId,
            `🆘 *Driver Help*\n\n• *Open Driver Panel* — Full web interface with map, orders, documents\n• *Share Location* — Update your GPS location\n• *Go Online/Offline* — Set your availability\n• *Upload Docs* — Submit required documents\n\nCommands:\n/start — Main menu\n/panel — Open Driver WebApp\n\nFor support contact your restaurant admin.`,
            { parse_mode: 'Markdown' }
        );
        return;
    }

    try {
        const driver = await getDriver(telegramUserId);
        if (driver && !session.step) {
            return sendMainMenu(chatId, driver, telegramUserId);
        }
    } catch (e) {
        console.error('Message handler error:', e);
    }
});

bot.on('polling_error', (err) => console.error('Driver bot polling error:', err.message));

module.exports = bot;
