require('dotenv').config({ path: require('path').join(__dirname, '../.env.example') });

const TelegramBot = require('node-telegram-bot-api');
const store = require('./store');

const DRIVER_BOT_TOKEN = process.env.DRIVER_BOT_TOKEN;
if (!DRIVER_BOT_TOKEN) { console.error('DRIVER_BOT_TOKEN missing in .env.example'); process.exit(1); }

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

async function sendMainMenu(chatId, driver) {
    const statusText = driver.is_available ? '🟢 Available' : '🔴 Busy';
    const approvedText = driver.is_approved ? '✅ Approved' : '⏳ Pending Approval';
    await bot.sendMessage(chatId,
        `🚗 *Driver Panel*\n\nName: ${driver.name}\nStatus: ${statusText}\nAccount: ${approvedText}`,
        {
            parse_mode: 'Markdown',
            reply_markup: {
                keyboard: [
                    [{ text: '📦 My Orders' }, { text: driver.is_available ? '🔴 Go Offline' : '🟢 Go Online' }],
                    [{ text: '📍 Share Location', request_location: true }, { text: '📊 My Stats' }],
                    [{ text: '🆘 Help' }]
                ],
                resize_keyboard: true
            }
        }
    );
}

bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const session = getSession(telegramUserId);

    try {
        const existing = await getDriver(telegramUserId);
        if (existing) {
            await bot.sendMessage(chatId, `👋 Welcome back, *${existing.name}*!`, { parse_mode: 'Markdown' });
            return sendMainMenu(chatId, existing);
        }

        session.step = 'register_name';
        session.data = {};
        bot.sendMessage(chatId,
            `👋 Welcome to *ET-FOOD Driver Bot*!\n\nTo get started, I need a few details. You'll be verified by our team before you can accept deliveries.\n\n📝 *Step 1/3:* Please enter your *full name*:`,
            { parse_mode: 'Markdown' }
        );
    } catch (e) {
        console.error('Start error:', e);
        bot.sendMessage(chatId, '❌ An error occurred. Please try again.');
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
            bot.sendMessage(chatId, '📍 Location updated successfully!');
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

    try {
        const driver = await getDriver(telegramUserId);
        if (!driver) return;

        if (text === '📦 My Orders') {
            const orders = await store.findMany('orders', { status: 'out_for_delivery' }, 'created_at');
            const myOrders = orders.filter(o => o.driver_id === driver.id);
            if (!myOrders.length) {
                return bot.sendMessage(chatId, '📭 No active deliveries right now.');
            }
            for (const o of myOrders) {
                bot.sendMessage(chatId,
                    `🚗 *Active Delivery*\n\nOrder: #${o.order_number}\nCustomer: ${o.customer_name}\nPhone: ${o.customer_phone}\nAddress: ${o.customer_address || 'Not provided'}\nTotal: ${o.total_amount} ETB`,
                    { parse_mode: 'Markdown' }
                );
            }
            return;
        }

        if (text === '🟢 Go Online' || text === '🔴 Go Offline') {
            const goOnline = text === '🟢 Go Online';
            if (!driver.is_approved && goOnline) {
                return bot.sendMessage(chatId, '⏳ Your account is still pending approval. Please wait for admin confirmation.');
            }
            await store.updateOne('drivers', { telegram_user_id: telegramUserId }, { is_available: goOnline });
            const updated = await getDriver(telegramUserId);
            bot.sendMessage(chatId, goOnline ? '🟢 You are now *online* and available for deliveries!' : '🔴 You are now *offline*.', { parse_mode: 'Markdown' });
            return sendMainMenu(chatId, updated);
        }

        if (text === '📊 My Stats') {
            return bot.sendMessage(chatId,
                `📊 *Your Stats*\n\nTotal Deliveries: ${driver.total_deliveries || 0}\nRating: ${driver.rating || 5.0} ⭐\nStatus: ${driver.is_available ? 'Online' : 'Offline'}\nAccount: ${driver.is_approved ? 'Approved' : 'Pending'}`,
                { parse_mode: 'Markdown' }
            );
        }

        if (text === '🆘 Help') {
            return bot.sendMessage(chatId,
                `🆘 *Driver Help*\n\n• *Go Online/Offline* — Set your availability\n• *My Orders* — View active deliveries\n• *Share Location* — Update your GPS location\n• *My Stats* — View your performance\n\nFor support contact your restaurant admin.`,
                { parse_mode: 'Markdown' }
            );
        }
    } catch (e) {
        console.error('Message handler error:', e);
    }
});

bot.on('polling_error', (err) => console.error('Driver bot polling error:', err.message));

module.exports = bot;
