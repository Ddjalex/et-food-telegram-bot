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

async function notifyDriverApproved(driver) {
    const bot = getDriverBot();
    if (!bot || !driver.telegram_user_id) return;
    try {
        await bot.sendMessage(driver.telegram_user_id,
            `🎉 *Congratulations, ${driver.name}!*\n\n` +
            `✅ Your driver account has been *approved*!\n\n` +
            `You can now:\n` +
            `• Go online to receive delivery orders\n` +
            `• Share your location to get matched with nearby orders\n\n` +
            `Open the driver bot and press *Go Online* to start earning!`,
            {
                parse_mode: 'Markdown',
                reply_markup: {
                    keyboard: [
                        [{ text: '🟢 Go Online' }, { text: '📦 My Orders' }],
                        [{ text: '📍 Share Location', request_location: true }, { text: '📊 My Stats' }]
                    ],
                    resize_keyboard: true
                }
            }
        );
        console.log(`Approval notification sent to driver ${driver.name} (${driver.telegram_user_id})`);
    } catch (e) {
        console.error(`Failed to send approval notification to driver ${driver.name}:`, e.message);
    }
}

async function notifyDriverRejected(driver, reason) {
    const bot = getDriverBot();
    if (!bot || !driver.telegram_user_id) return;
    try {
        await bot.sendMessage(driver.telegram_user_id,
            `❌ *Driver Application Update*\n\n` +
            `Hi ${driver.name}, unfortunately your driver application has been *rejected*.\n\n` +
            `📋 *Reason:* ${reason || 'Does not meet current requirements'}\n\n` +
            `If you believe this is a mistake or have questions, please contact your restaurant admin.\n\n` +
            `You may re-apply by using /start in the driver bot.`,
            { parse_mode: 'Markdown' }
        );
        console.log(`Rejection notification sent to driver ${driver.name} (${driver.telegram_user_id})`);
    } catch (e) {
        console.error(`Failed to send rejection notification to driver ${driver.name}:`, e.message);
    }
}

async function notifyCustomerOrderStatus(telegramUserId, order, statusMessage) {
    const bot = getCustomerBot();
    if (!bot || !telegramUserId) return;
    try {
        const statusEmoji = {
            pending: '⏳', confirmed: '✅', preparing: '👨‍🍳',
            ready: '🔔', out_for_delivery: '🚗', delivered: '✅', cancelled: '❌'
        }[order.status] || '📦';

        await bot.sendMessage(telegramUserId,
            `${statusEmoji} *Order Update — #${order.order_number}*\n\n` +
            `${statusMessage}\n\n` +
            `Total: *${order.total_amount} ETB*`,
            { parse_mode: 'Markdown' }
        );
        console.log(`Order status notification sent to customer ${telegramUserId}`);
    } catch (e) {
        console.error(`Failed to send order notification to customer ${telegramUserId}:`, e.message);
    }
}

module.exports = { notifyDriverApproved, notifyDriverRejected, notifyCustomerOrderStatus };
