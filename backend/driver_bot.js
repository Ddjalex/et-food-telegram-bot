const TelegramBot = require('node-telegram-bot-api');
const store = require('./store');

const DRIVER_BOT_TOKEN = process.env.DRIVER_BOT_TOKEN;
if (!DRIVER_BOT_TOKEN) { console.error('DRIVER_BOT_TOKEN secret is not set'); process.exit(1); }

// Always show the last 6 digits of the order number for consistency across all dashboards
function shortNum(order) {
    return (order.order_number || order.id || '').toString().slice(-6).toUpperCase();
}

const bot = new TelegramBot(DRIVER_BOT_TOKEN, { polling: false });

async function startDriverBot(retries = 5) {
    try {
        await bot.deleteWebHook({ drop_pending_updates: true });
        // Wait for Telegram to release the old session
        await new Promise(r => setTimeout(r, 3000));
        bot.startPolling({
            restart: false,
            params: { allowed_updates: ['message', 'edited_message', 'callback_query'] }
        });
        console.log('Driver bot started.');
    } catch (err) {
        console.error('Driver bot start error:', err.message);
        if (retries > 0) {
            console.log(`Retrying in 5s... (${retries} attempts left)`);
            await new Promise(r => setTimeout(r, 5000));
            return startDriverBot(retries - 1);
        }
    }
}

bot.on('polling_error', async (err) => {
    if (err.code === 'ETELEGRAM' && err.message.includes('409')) {
        console.log('Driver bot: 409 conflict detected, restarting polling...');
        try { bot.stopPolling(); } catch(e) {}
        await new Promise(r => setTimeout(r, 5000));
        try {
            await bot.deleteWebHook({ drop_pending_updates: true });
            await new Promise(r => setTimeout(r, 2000));
            bot.startPolling({ restart: false, params: { allowed_updates: ['message', 'edited_message', 'callback_query'] } });
        } catch(e) { console.error('Driver bot recovery error:', e.message); }
    }
});

startDriverBot();

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
    // Include a timestamp so Telegram never serves a cached version of the panel
    return `${base}/driver-panel?driver_id=${telegramUserId}&v=${Date.now()}`;
}

async function sendMainMenu(chatId, driver, telegramUserId) {
    const statusText = driver.is_available ? '🟢 Online' : '🔴 Offline';
    const approvedText = driver.is_approved ? '✅ Approved' : '⏳ Pending Approval';
    const webAppUrl = getWebAppUrl(telegramUserId || driver.telegram_user_id);

    const menuRows = [];
    // Only show Open Driver Panel when driver is online
    if (driver.is_available) {
        menuRows.push([{ text: '🗂️ Open Driver Panel', web_app: { url: webAppUrl } }]);
    }
    menuRows.push([
        { text: driver.is_available ? '🔴 Go Offline' : '🟢 Go Online', callback_data: driver.is_available ? 'go_offline' : 'go_online' },
        { text: '📊 My Stats', callback_data: 'my_stats' }
    ]);
    menuRows.push([
        { text: '📦 My Orders', callback_data: 'my_orders' },
        { text: '📁 Upload Docs', callback_data: 'upload_docs' }
    ]);

    const offlineHint = driver.is_available
        ? ''
        : '\n\nTap *🟢 Go Online* then share your live location to start receiving orders.';

    await bot.sendMessage(chatId,
        `🚗 *Driver Panel*\n\n👤 Name: ${driver.name}\n📊 Status: ${statusText}\n🏷️ Account: ${approvedText}${offlineHint}`,
        {
            parse_mode: 'Markdown',
            reply_markup: { inline_keyboard: menuRows }
        }
    );

    // If driver is online but has no recent location, prompt them to share
    if (driver.is_available && !driver.current_lat) {
        await bot.sendMessage(chatId,
            `📍 *Share your live location* so orders can be matched to you in real-time.\n\n` +
            `Choose *"Share My Live Location for..."* (not just current location) so the system always knows where you are.`,
            {
                parse_mode: 'Markdown',
                reply_markup: {
                    keyboard: [
                        [{ text: '📍 Share My Live Location', request_location: true }],
                        [{ text: '🆘 Help' }]
                    ],
                    resize_keyboard: true
                }
            }
        );
    }
}

bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const session = getSession(telegramUserId);

    try {
        let existing = await getDriver(telegramUserId);

        if (existing) {
            // Resume incomplete registration if phone or vehicle not yet set
            if (!existing.phone_number || existing.phone_number === '') {
                session.step = 'register_phone';
                session.data = { name: existing.name };
                return bot.sendMessage(chatId,
                    `👋 Welcome back, *${existing.name}*! Let's finish your registration.\n\n📞 *Step 2/3:* Enter your *phone number* (e.g. +251911234567):`,
                    { parse_mode: 'Markdown', reply_markup: { remove_keyboard: true } }
                );
            }
            if (!existing.vehicle_type || existing.vehicle_type === 'pending') {
                session.step = 'register_vehicle';
                session.data = { name: existing.name, phone_number: existing.phone_number };
                return bot.sendMessage(chatId,
                    `👋 Welcome back, *${existing.name}*! One last step.\n\n🚗 *Step 3/3:* Select your *vehicle type*:`,
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

            // Fully registered driver — reset stale location if needed
            const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
            const locationStale = !existing.current_lat ||
                !existing.last_location_update ||
                new Date(existing.last_location_update) < twoHoursAgo;

            if (existing.is_available && locationStale) {
                await store.updateOne('drivers', { telegram_user_id: telegramUserId }, {
                    is_available: false,
                    current_lat: null,
                    current_lng: null
                });
                existing = await getDriver(telegramUserId);
                await bot.sendMessage(chatId,
                    `👋 Welcome back, *${existing.name}*!\n\n` +
                    `⚠️ Your status was reset to *Offline* — your live location is no longer active.\n\n` +
                    `Tap *🟢 Go Online* and share your live location to start receiving orders.`,
                    { parse_mode: 'Markdown' }
                );
            } else {
                await bot.sendMessage(chatId, `👋 Welcome back, *${existing.name}*!`, { parse_mode: 'Markdown' });
            }
            session.step = null;
            session.data = {};
            return sendMainMenu(chatId, existing, telegramUserId);
        }

        // New driver — start registration
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

            if (!goOnline) {
                // Going offline — immediate, no location needed
                await store.updateOne('drivers', { telegram_user_id: telegramUserId }, { is_available: false });
                bot.answerCallbackQuery(query.id, { text: '🔴 You are now Offline.' });
                const updated = await getDriver(telegramUserId);
                return sendMainMenu(chatId, updated, telegramUserId);
            }

            // Going online — require live location first
            bot.answerCallbackQuery(query.id, { text: '📍 Please share your live location to go online.' });
            const session = getSession(telegramUserId);
            session.pendingOnline = true;
            return bot.sendMessage(chatId,
                `📍 *Share your live location to go online*\n\n` +
                `Tap the button below and choose *"Share My Live Location for..."*\n` +
                `(not just current location — live location lets us match you to nearby orders in real-time)`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: {
                        keyboard: [
                            [{ text: '📍 Share Live Location to Go Online', request_location: true }],
                            [{ text: '❌ Cancel' }]
                        ],
                        resize_keyboard: true,
                        one_time_keyboard: true
                    }
                }
            );
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
                    `🚗 *Active Delivery*\n\nOrder: #${shortNum(o)}\nCustomer: ${o.customer_name}\nPhone: ${o.customer_phone}\nAddress: ${o.customer_address || 'Not provided'}\nTotal: ${o.total_amount} ETB`,
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
                `📁 *Upload Documents*\n\nUpload your required documents (ID, driver\'s license, vehicle registration) via the Driver Panel.`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: {
                        inline_keyboard: [[{ text: '📁 Open Document Upload', web_app: { url: webAppUrl } }]]
                    }
                }
            );
            return;
        }

        // ── ORDER ACCEPT / DECLINE ──────────────────────────────
        if (data.startsWith('accept_order:')) {
            const orderId = data.split(':')[1];
            bot.answerCallbackQuery(query.id, { text: '⏳ Processing...' });

            const { handleDriverAccept } = require('./driver_assignment');
            const result = await handleDriverAccept(orderId, telegramUserId);

            if (result.alreadyTaken) {
                return bot.sendMessage(chatId,
                    `⚡ *Too Late!*\n\nAnother driver already accepted this order. Keep an eye out for the next one!`,
                    { parse_mode: 'Markdown' }
                );
            }

            if (!result.success) {
                return bot.sendMessage(chatId,
                    `❌ Could not accept order: ${result.error || 'Unknown error'}`,
                    { parse_mode: 'Markdown' }
                );
            }

            const { order, driver: assignedDriver } = result;

            // Notify the driver with order details + navigation buttons
            await bot.sendMessage(chatId,
                `✅ *Order Accepted!*\n\n` +
                `📦 Order: *#${shortNum(order)}*\n` +
                `👤 Customer: ${order.customer_name || 'N/A'}\n` +
                `📞 Phone: ${order.customer_phone || 'N/A'}\n` +
                `📍 Deliver to: ${order.customer_address || 'See address'}\n\n` +
                `💰 Total: *${order.total_amount} ETB*\n` +
                `💳 Payment: ${order.payment_method || 'cash'}\n\n` +
                `👇 Use the buttons below to navigate:`,
                {
                    parse_mode: 'Markdown',
                    reply_markup: {
                        inline_keyboard: [
                            [{ text: '🏪 Navigate to Restaurant', callback_data: `nav_restaurant:${order.id}` }],
                            [{ text: '🏠 Navigate to Customer', callback_data: `nav_customer:${order.id}` }],
                            [{ text: '✅ Mark as Picked Up', callback_data: `picked_up:${order.id}` }]
                        ]
                    }
                }
            );

            // Notify the customer
            const { notifyCustomerDriverAssigned } = require('./notifier');
            if (order.telegram_user_id) {
                notifyCustomerDriverAssigned(order.telegram_user_id, order, assignedDriver)
                    .catch(e => console.error('[DriverBot] customer notify error:', e.message));
            }

            return;
        }

        if (data.startsWith('decline_order:')) {
            bot.answerCallbackQuery(query.id, { text: '❌ Order declined.' });
            bot.sendMessage(chatId, `✅ You declined that order. Stay ready for the next one!`);
            return;
        }

        // ── NAVIGATE TO RESTAURANT ──────────────────────────────
        if (data.startsWith('nav_restaurant:')) {
            const orderId = data.split(':')[1];
            bot.answerCallbackQuery(query.id, { text: '📍 Loading restaurant location...' });
            try {
                const order = await store.findById('orders', orderId);
                if (!order) return bot.sendMessage(chatId, '❌ Order not found.');
                const restaurant = order.restaurant_id
                    ? await store.findOne('restaurants', { id: order.restaurant_id }).catch(() => null)
                    : null;
                const lat = restaurant ? parseFloat(restaurant.lat) : null;
                const lng = restaurant ? parseFloat(restaurant.lng) : null;
                const name = restaurant ? restaurant.name : 'Restaurant';

                if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
                    await bot.sendMessage(chatId,
                        `🏪 *Navigate to ${name}*\n\nTap the location below to open in Telegram Maps, or use the navigation app buttons:`,
                        {
                            parse_mode: 'Markdown',
                            reply_markup: {
                                inline_keyboard: [
                                    [
                                        { text: '📍 Open in Google Maps', url: `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving` }
                                    ],
                                    [{ text: '🏠 Navigate to Customer', callback_data: `nav_customer:${orderId}` }]
                                ]
                            }
                        }
                    );
                    await bot.sendLocation(chatId, lat, lng);
                } else {
                    await bot.sendMessage(chatId,
                        `🏪 *${name}*\n\nNo GPS coordinates saved for this restaurant. Please use the address to navigate manually.`,
                        { parse_mode: 'Markdown' }
                    );
                }
            } catch (e) {
                console.error('nav_restaurant error:', e);
                bot.sendMessage(chatId, '❌ Could not load restaurant location.');
            }
            return;
        }

        // ── NAVIGATE TO CUSTOMER ──────────────────────────────
        if (data.startsWith('nav_customer:')) {
            const orderId = data.split(':')[1];
            bot.answerCallbackQuery(query.id, { text: '📍 Loading customer location...' });
            try {
                const order = await store.findById('orders', orderId);
                if (!order) return bot.sendMessage(chatId, '❌ Order not found.');
                const lat = order.location_lat ? parseFloat(order.location_lat) : null;
                const lng = order.location_lng ? parseFloat(order.location_lng) : null;

                if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
                    await bot.sendMessage(chatId,
                        `🏠 *Navigate to ${order.customer_name || 'Customer'}*\n📍 ${order.customer_address || 'See location below'}\n\nTap the location below to open in Telegram Maps, or use the navigation app buttons:`,
                        {
                            parse_mode: 'Markdown',
                            reply_markup: {
                                inline_keyboard: [
                                    [
                                        { text: '📍 Open in Google Maps', url: `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving` }
                                    ],
                                    [{ text: '✅ Mark as Delivered', callback_data: `mark_delivered:${orderId}` }]
                                ]
                            }
                        }
                    );
                    await bot.sendLocation(chatId, lat, lng);
                } else {
                    await bot.sendMessage(chatId,
                        `🏠 *Customer: ${order.customer_name || 'N/A'}*\n📍 Address: ${order.customer_address || 'Not provided'}\n📞 Phone: ${order.customer_phone || 'N/A'}\n\n⚠️ No GPS coordinates from customer. Use the address or call them.`,
                        {
                            parse_mode: 'Markdown',
                            reply_markup: {
                                inline_keyboard: [
                                    [{ text: '✅ Mark as Delivered', callback_data: `mark_delivered:${orderId}` }]
                                ]
                            }
                        }
                    );
                }
            } catch (e) {
                console.error('nav_customer error:', e);
                bot.sendMessage(chatId, '❌ Could not load customer location.');
            }
            return;
        }

        // ── MARK AS PICKED UP ──────────────────────────────
        if (data.startsWith('picked_up:')) {
            const orderId = data.split(':')[1];
            bot.answerCallbackQuery(query.id, { text: '✅ Marked as picked up!' });
            try {
                const order = await store.findById('orders', orderId);
                if (!order) return bot.sendMessage(chatId, '❌ Order not found.');
                const { notifyCustomerOrderPickedUp } = require('./notifier');
                if (order.telegram_user_id) {
                    notifyCustomerOrderPickedUp(order.telegram_user_id, order, driver)
                        .catch(e => console.error('[DriverBot] picked up notify error:', e.message));
                }
                await bot.sendMessage(chatId,
                    `🚗 *Order Picked Up!*\n\nYou have picked up order *#${shortNum(order)}*.\nNow navigate to the customer and deliver it!`,
                    {
                        parse_mode: 'Markdown',
                        reply_markup: {
                            inline_keyboard: [
                                [{ text: '🏠 Navigate to Customer', callback_data: `nav_customer:${orderId}` }],
                                [{ text: '✅ Mark as Delivered', callback_data: `mark_delivered:${orderId}` }]
                            ]
                        }
                    }
                );
            } catch (e) {
                console.error('picked_up error:', e);
                bot.sendMessage(chatId, '❌ Could not update order status.');
            }
            return;
        }

        // ── MARK AS DELIVERED ──────────────────────────────
        if (data.startsWith('mark_delivered:')) {
            const orderId = data.split(':')[1];
            bot.answerCallbackQuery(query.id, { text: '✅ Marking as delivered...' });
            try {
                const base = process.env.REPLIT_DEV_DOMAIN
                    ? `https://${process.env.REPLIT_DEV_DOMAIN}`
                    : 'http://localhost:5000';
                const resp = await fetch(`${base}/api/orders/${orderId}/delivered`, { method: 'POST' });
                const json = await resp.json();
                if (json.success) {
                    const fee = json.driver_fee || 0;
                    const dist = json.distance_km || 0;
                    await bot.sendMessage(chatId,
                        `🎉 *Delivery Complete!*\n\n` +
                        `Order has been marked as delivered.\n\n` +
                        `📍 Distance: *${dist > 0 ? dist.toFixed(1) + ' km' : 'N/A'}*\n` +
                        `💰 Your delivery fee: *${fee} ETB*\n\n` +
                        `Thank you! You are now available for new orders. 🚗`,
                        { parse_mode: 'Markdown' }
                    );
                } else {
                    bot.sendMessage(chatId, `❌ Could not mark as delivered: ${json.error || 'Unknown error'}`);
                }
            } catch (e) {
                console.error('mark_delivered error:', e);
                bot.sendMessage(chatId, '❌ Failed to mark order as delivered. Please try again.');
            }
            return;
        }

    } catch (e) {
        console.error('Callback query error:', e);
        bot.answerCallbackQuery(query.id, { text: 'An error occurred.' });
    }
});

// ============================================================
// LOCATION MESSAGES — initial location share
// ============================================================

bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const telegramUserId = String(msg.from.id);
    const text = msg.text || '';
    const session = getSession(telegramUserId);

    if (msg.location) {
        try {
            const driver = await getDriver(telegramUserId);
            if (!driver) return bot.sendMessage(chatId, '❌ You are not registered. Use /start to register.');

            const isLive = msg.location.live_period && msg.location.live_period > 0;
            const updates = {
                current_lat: msg.location.latitude,
                current_lng: msg.location.longitude,
                last_location_update: new Date()
            };

            // If driver was waiting for location to go online, activate now
            if (session.pendingOnline) {
                updates.is_available = true;
                session.pendingOnline = false;
                await store.updateOne('drivers', { telegram_user_id: telegramUserId }, updates);
                const updated = await getDriver(telegramUserId);
                bot.sendMessage(chatId,
                    `✅ *You are now Online!*\n\n📍 Location saved. You will receive nearby order assignments.\n\n${isLive ? '🔴 Live location is active — your position updates automatically.' : '💡 Tip: For best results, use *Live Location* so we can track you in real-time.'}`,
                    { parse_mode: 'Markdown', reply_markup: { remove_keyboard: true } }
                );
                return sendMainMenu(chatId, updated, telegramUserId);
            }

            // Live location while offline — automatically go online
            if (isLive && !driver.is_available) {
                updates.is_available = true;
                session.pendingOnline = false;
                await store.updateOne('drivers', { telegram_user_id: telegramUserId }, updates);
                const updated = await getDriver(telegramUserId);
                const webAppUrl = getWebAppUrl(telegramUserId);
                await bot.sendMessage(chatId,
                    `✅ *You are now Online!*\n\n📍 Live location active — your position updates automatically.\nYou will now receive nearby order assignments.`,
                    {
                        parse_mode: 'Markdown',
                        reply_markup: { remove_keyboard: true }
                    }
                );
                return bot.sendMessage(chatId, '🗂️ Open your Driver Panel to manage orders:', {
                    reply_markup: {
                        inline_keyboard: [[{ text: '🗂️ Open Driver Panel', web_app: { url: webAppUrl } }]]
                    }
                });
            }

            // Normal location update (driver already online)
            await store.updateOne('drivers', { telegram_user_id: telegramUserId }, updates);

            if (isLive) {
                const webAppUrl = getWebAppUrl(telegramUserId);
                bot.sendMessage(chatId,
                    `📍 *Live Location Active!*\n\nYour position will update automatically as you move.\nYou will now receive nearby order assignments.`,
                    {
                        parse_mode: 'Markdown',
                        reply_markup: {
                            inline_keyboard: [[{ text: '🗂️ Open Driver Panel', web_app: { url: webAppUrl } }]]
                        }
                    }
                );
            } else {
                bot.sendMessage(chatId,
                    `📍 Location updated! ✅\n\n💡 *Tip:* Share your *Live Location* for real-time order matching — choose "Share My Live Location for..." instead of current location.`,
                    { parse_mode: 'Markdown' }
                );
            }
        } catch (e) {
            console.error('Location update error:', e);
        }
        return;
    }

    if (text.startsWith('/')) return;

    // Cancel pending go-online
    if (text === '❌ Cancel' && session.pendingOnline) {
        session.pendingOnline = false;
        const driver = await getDriver(telegramUserId);
        bot.sendMessage(chatId, '↩️ Cancelled. You are still Offline.', { reply_markup: { remove_keyboard: true } });
        if (driver) return sendMainMenu(chatId, driver, telegramUserId);
        return;
    }

    if (session.step === 'register_name') {
        if (text.length < 2) return bot.sendMessage(chatId, '⚠️ Please enter a valid full name (at least 2 characters).');
        const name = text.trim();
        session.data.name = name;
        session.step = 'register_phone';
        try {
            // Save driver to DB immediately so a bot restart won't lose progress
            const existing = await getDriver(telegramUserId);
            if (!existing) {
                await store.insertOne('drivers', {
                    name,
                    phone_number: '',
                    telegram_user_id: telegramUserId,
                    vehicle_type: 'pending',
                    is_active: true,
                    is_available: false,
                    is_approved: false,
                    total_deliveries: 0,
                    rating: 5.0
                });
            } else {
                await store.updateOne('drivers', { telegram_user_id: telegramUserId }, { name });
            }
        } catch (e) {
            console.error('Registration step 1 save error:', e);
        }
        return bot.sendMessage(chatId, `✅ Name saved: *${name}*\n\n📞 *Step 2/3:* Enter your *phone number* (e.g. +251911234567):`, { parse_mode: 'Markdown' });
    }

    if (session.step === 'register_phone') {
        if (text.length < 7) return bot.sendMessage(chatId, '⚠️ Please enter a valid phone number.');
        const phone = text.trim();
        session.data.phone_number = phone;
        session.step = 'register_vehicle';
        try {
            await store.updateOne('drivers', { telegram_user_id: telegramUserId }, { phone_number: phone });
        } catch (e) {
            console.error('Registration step 2 save error:', e);
        }
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
            await store.updateOne('drivers', { telegram_user_id: telegramUserId }, { vehicle_type: vehicle });
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
            `🆘 *Driver Help*\n\n• *Open Driver Panel* — Full web interface with map, orders, documents\n• *Share Live Location* — Update your GPS in real-time (choose "Share Live Location for...")\n• *Go Online/Offline* — Set your availability\n• *Upload Docs* — Submit required documents\n\nCommands:\n/start — Main menu\n/panel — Open Driver WebApp\n\nFor support contact your restaurant admin.`,
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

// ============================================================
// LIVE LOCATION UPDATES — Telegram sends edited_message as driver moves
// This is the correct Telegram API for real-time location (not message, but edited_message)
// ============================================================

bot.on('edited_message', async (msg) => {
    if (!msg.location) return;
    const telegramUserId = String(msg.from.id);
    const { latitude, longitude, live_period } = msg.location;

    try {
        const driver = await getDriver(telegramUserId);
        if (!driver) return;

        await store.updateOne('drivers', { telegram_user_id: telegramUserId }, {
            current_lat: latitude,
            current_lng: longitude,
            last_location_update: new Date()
        });

        console.log(`📍 Driver live location update — ${driver.name} (${telegramUserId}): ${latitude.toFixed(5)}, ${longitude.toFixed(5)}${live_period ? ` (live)` : ''}`);
    } catch (e) {
        console.error('Driver live location update error:', e.message);
    }
});

bot.on('polling_error', (err) => console.error('Driver bot polling error:', err.message));

module.exports = bot;
