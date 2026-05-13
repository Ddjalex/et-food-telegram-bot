const TelegramBot = require('node-telegram-bot-api');

let driverBot = null;
let customerBot = null;

function getDriverBot() {
    if (!driverBot && process.env.DRIVER_BOT_TOKEN) {
        driverBot = new TelegramBot(process.env.DRIVER_BOT_TOKEN);
    }
    return driverBot;
}

function getCustomerBot() {
    if (!customerBot && process.env.BOT_TOKEN) {
        customerBot = new TelegramBot(process.env.BOT_TOKEN);
    }
    return customerBot;
}

async function safeSend(bot, chatId, text, options = {}) {
    if (!bot || !chatId) return;
    try {
        await bot.sendMessage(chatId, text, { parse_mode: 'Markdown', ...options });
    } catch (e) {
        console.error(`Telegram send failed to ${chatId}:`, e.message);
    }
}

// ============================================================
// DRIVER NOTIFICATIONS
// ============================================================

async function notifyDriverApproved(driver) {
    const bot = getDriverBot();
    if (!bot || !driver.telegram_user_id) return;
    await safeSend(bot, driver.telegram_user_id,
        `🎉 *Congratulations, ${driver.name}!*\n\n` +
        `✅ Your driver account has been *approved*!\n\n` +
        `You can now:\n` +
        `• Go online to receive delivery orders\n` +
        `• Share your *live location* to get matched with nearby orders\n\n` +
        `Open the driver bot and press *Go Online* to start earning!`,
        {
            reply_markup: {
                keyboard: [
                    [{ text: '🟢 Go Online' }, { text: '📦 My Orders' }],
                    [{ text: '📍 Share My Live Location', request_location: true }, { text: '📊 My Stats' }]
                ],
                resize_keyboard: true
            }
        }
    );
    console.log(`Approval notification sent to driver ${driver.name} (${driver.telegram_user_id})`);
}

async function notifyDriverRejected(driver, reason) {
    const bot = getDriverBot();
    if (!bot || !driver.telegram_user_id) return;
    await safeSend(bot, driver.telegram_user_id,
        `❌ *Driver Application Update*\n\n` +
        `Hi ${driver.name}, unfortunately your driver application has been *rejected*.\n\n` +
        `📋 *Reason:* ${reason || 'Does not meet current requirements'}\n\n` +
        `If you believe this is a mistake, please contact your restaurant admin.\n\n` +
        `You may re-apply by using /start in the driver bot.`
    );
    console.log(`Rejection notification sent to driver ${driver.name} (${driver.telegram_user_id})`);
}

async function notifyDriverNewOrder(driver, order) {
    const bot = getDriverBot();
    if (!bot || !driver.telegram_user_id) return;

    let itemsSummary = '';
    try {
        const items = typeof order.items === 'string' ? JSON.parse(order.items) : order.items;
        if (Array.isArray(items)) {
            itemsSummary = items.slice(0, 3).map(i => `  • ${i.name} x${i.quantity}`).join('\n');
            if (items.length > 3) itemsSummary += `\n  • ...+${items.length - 3} more`;
        }
    } catch (_) {}

    await safeSend(bot, driver.telegram_user_id,
        `🔔 *New Delivery Order!*\n\n` +
        `📦 Order: *#${order.order_number}*\n` +
        `👤 Customer: ${order.customer_name}\n` +
        `📞 Phone: ${order.customer_phone || 'N/A'}\n` +
        `📍 Address: ${order.customer_address || 'See map'}\n` +
        (itemsSummary ? `\n🛒 *Items:*\n${itemsSummary}\n` : '') +
        `\n💰 Total: *${order.total_amount} ETB*\n` +
        `💳 Payment: ${order.payment_method || 'cash'}\n\n` +
        `⚡ First driver to accept gets this order!`
    );
    console.log(`New order notification sent to driver ${driver.name} (${driver.telegram_user_id})`);
}

// ============================================================
// CUSTOMER NOTIFICATIONS
// ============================================================

async function notifyCustomerOrderStatus(telegramUserId, order, statusMessage) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    const statusEmoji = {
        pending: '⏳', confirmed: '✅', kitchen_confirmed: '👨‍🍳',
        preparing: '👨‍🍳', ready: '🔔', out_for_delivery: '🚗',
        delivered: '✅', cancelled: '❌'
    }[order.status] || '📦';

    await safeSend(bot, telegramUserId,
        `${statusEmoji} *Order Update — #${order.order_number}*\n\n` +
        `${statusMessage}\n\n` +
        `💰 Total: *${order.total_amount} ETB*`
    );
    console.log(`Order status notification sent to customer ${telegramUserId}`);
}

async function notifyCustomerOrderReceived(telegramUserId, order) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    await safeSend(bot, telegramUserId,
        `✅ *Order Received! #${order.order_number}*\n\n` +
        `🍽️ Your order has been sent to the kitchen.\n` +
        `⏳ Waiting for kitchen confirmation...\n\n` +
        `💰 Total: *${order.total_amount} ETB*\n\n` +
        `We'll notify you as soon as the kitchen confirms! 🔔`,
        {
            reply_markup: {
                inline_keyboard: [[
                    { text: '📦 View My Orders', callback_data: 'orders:active' }
                ]]
            }
        }
    );
}

async function notifyCustomerKitchenAccepted(telegramUserId, order) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    await safeSend(bot, telegramUserId,
        `👨‍🍳 *Kitchen Accepted Your Order!*\n\n` +
        `Order *#${order.order_number}* is now being prepared.\n\n` +
        `🍳 The chef is cooking your food right now!\n` +
        `🚗 A driver will be assigned soon.\n\n` +
        `💰 Total: *${order.total_amount} ETB*\n\n` +
        `We'll let you know when your order is on the way! 🔔`,
        {
            reply_markup: {
                inline_keyboard: [[
                    { text: '📦 Track My Order', callback_data: 'orders:active' }
                ]]
            }
        }
    );
}

async function notifyCustomerKitchenRejected(telegramUserId, order, reason) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    await safeSend(bot, telegramUserId,
        `❌ *Order Cancelled — #${order.order_number}*\n\n` +
        `Unfortunately the kitchen could not accept your order.\n\n` +
        `📋 *Reason:* ${reason || 'Items currently unavailable'}\n\n` +
        `💳 If you paid, a refund will be processed shortly.\n\n` +
        `Please try ordering again or choose different items! 🍔`,
        {
            reply_markup: {
                inline_keyboard: [[
                    { text: '🍔 Order Again', web_app: { url: process.env.WEBAPP_URL || `https://${process.env.REPLIT_DEV_DOMAIN}` } }
                ]]
            }
        }
    );
}

async function notifyCustomerPaymentVerified(telegramUserId, order) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    await safeSend(bot, telegramUserId,
        `✅ *Payment Verified! #${order.order_number}*\n\n` +
        `Your payment of *${order.total_amount} ETB* has been confirmed.\n\n` +
        `👨‍🍳 The kitchen will now prepare your order.\n` +
        `🚗 A driver will be assigned after preparation.\n\n` +
        `Thank you for your order! We'll keep you updated. 🔔`
    );
}

async function notifyCustomerDriverAssigned(telegramUserId, order, driver) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    const vehicleEmoji = { motorcycle: '🏍️', car: '🚗', bicycle: '🚲', scooter: '🛵' }[driver.vehicle_type] || '🚗';
    await safeSend(bot, telegramUserId,
        `🚗 *Driver Assigned! #${order.order_number}*\n\n` +
        `${vehicleEmoji} *Driver:* ${driver.name}\n` +
        `📞 *Phone:* ${driver.phone_number}\n` +
        `⭐ *Rating:* ${driver.rating || 5.0}\n\n` +
        `Your order is being picked up and is on the way! 🎉\n\n` +
        `💡 Your driver can see your live location in real-time.`
    );
}

async function notifyCustomerOrderPickedUp(telegramUserId, order, driver) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    await safeSend(bot, telegramUserId,
        `🚗 *Order Picked Up! #${order.order_number}*\n\n` +
        `${driver ? driver.name : 'Your driver'} has picked up your order and is heading to you!\n\n` +
        `📍 Make sure your location is shared so the driver can find you.\n\n` +
        `🍔 Your food is on the way! Estimated: 15–30 min`,
        {
            reply_markup: {
                inline_keyboard: [[
                    { text: '📦 Track My Order', callback_data: 'orders:active' }
                ]]
            }
        }
    );
}

async function notifyCustomerOrderDelivered(telegramUserId, order) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    await safeSend(bot, telegramUserId,
        `🎉 *Order Delivered! #${order.order_number}*\n\n` +
        `Your food has been delivered. Enjoy your meal! 🍽️\n\n` +
        `💰 Total paid: *${order.total_amount} ETB*\n\n` +
        `Thank you for choosing ET-FOOD! Come back soon. 🙏`,
        {
            reply_markup: {
                inline_keyboard: [[
                    { text: '🍔 Order Again', web_app: { url: process.env.WEBAPP_URL || `https://${process.env.REPLIT_DEV_DOMAIN}` } }
                ]]
            }
        }
    );
}

async function notifyCustomerDeliveryPriceConfirmation(telegramUserId, order) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;

    // Build items list
    let itemsText = '';
    let foodSubtotal = 0;
    try {
        const items = typeof order.items === 'string' ? JSON.parse(order.items) : order.items;
        if (Array.isArray(items) && items.length) {
            itemsText = items.map(i => {
                const lineTotal = parseFloat(i.price) * parseInt(i.quantity);
                foodSubtotal += lineTotal;
                return `  • ${i.name} ×${i.quantity}  —  ${lineTotal.toFixed(0)} ETB`;
            }).join('\n');
        }
    } catch (_) {}

    const driverFee   = parseFloat(order.driver_fee || order.delivery_fee || 0);
    const distanceKm  = parseFloat(order.driver_distance_km || 0);
    const total       = parseFloat(order.total_amount || 0);

    let text = `🛵 *Your order has arrived! #${order.order_number}*\n\n`;
    text += `🍽️ *Order Summary*\n`;
    if (itemsText) text += `${itemsText}\n\n`;
    text += `─────────────────────\n`;
    text += `🛒 Food subtotal:  *${foodSubtotal > 0 ? foodSubtotal.toFixed(0) : (total - driverFee).toFixed(0)} ETB*\n`;
    if (distanceKm > 0) {
        text += `📍 Delivery distance:  *${distanceKm.toFixed(1)} km*\n`;
    }
    text += `🚗 Delivery fee:  *${driverFee.toFixed(0)} ETB*\n`;
    text += `─────────────────────\n`;
    text += `💰 *Total:  ${total.toFixed(0)} ETB*\n\n`;
    text += `Please confirm that you received your order and the price is correct.`;

    await safeSend(bot, telegramUserId, text, {
        reply_markup: {
            inline_keyboard: [
                [{ text: '✅ Accept & Confirm Delivery', callback_data: `confirm_delivery:${order.id}` }],
                [{ text: '📦 View Order Details', callback_data: `order:${order.id}` }]
            ]
        }
    });
}

async function notifyCustomerOrderCancelled(telegramUserId, order, reason) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    await safeSend(bot, telegramUserId,
        `❌ *Order Cancelled — #${order.order_number}*\n\n` +
        `Your order has been cancelled.\n\n` +
        (reason ? `📋 *Reason:* ${reason}\n\n` : '') +
        `💳 If you paid online, a refund will be processed.\n\n` +
        `Please contact us if you have any questions.`
    );
}

module.exports = {
    notifyDriverApproved,
    notifyDriverRejected,
    notifyDriverNewOrder,
    notifyCustomerOrderStatus,
    notifyCustomerOrderReceived,
    notifyCustomerKitchenAccepted,
    notifyCustomerKitchenRejected,
    notifyCustomerPaymentVerified,
    notifyCustomerDriverAssigned,
    notifyCustomerOrderPickedUp,
    notifyCustomerOrderDelivered,
    notifyCustomerOrderCancelled,
    notifyCustomerDeliveryPriceConfirmation
};
