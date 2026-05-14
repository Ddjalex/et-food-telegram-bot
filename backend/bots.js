const https = require('https');

async function forceDropSession(token, name) {
    return new Promise((resolve) => {
        const req = https.get(
            `https://api.telegram.org/bot${token}/deleteWebhook?drop_pending_updates=true`,
            (res) => {
                res.resume();
                console.log(`${name}: webhook cleared`);
                resolve();
            }
        );
        req.on('error', () => resolve());
        req.setTimeout(5000, () => { req.destroy(); resolve(); });
    });
}

async function main() {
    console.log('Starting ET-FOOD Telegram Bots...');

    const BOT_TOKEN = process.env.BOT_TOKEN;
    const DRIVER_BOT_TOKEN = process.env.DRIVER_BOT_TOKEN;

    if (!BOT_TOKEN)        { console.error('BOT_TOKEN secret is not set'); process.exit(1); }
    if (!DRIVER_BOT_TOKEN) { console.error('DRIVER_BOT_TOKEN secret is not set'); process.exit(1); }

    // Force-drop any existing sessions before loading bots
    await forceDropSession(BOT_TOKEN, 'Customer bot');
    await forceDropSession(DRIVER_BOT_TOKEN, 'Driver bot');

    // Wait for Telegram to fully release previous sessions
    console.log('Waiting for Telegram to release previous sessions...');
    await new Promise(r => setTimeout(r, 5000));

    // Start bots sequentially to avoid startup conflicts
    require('./customer_bot');
    await new Promise(r => setTimeout(r, 1000));
    require('./driver_bot');

    console.log('Both bots are running!');
}

main().catch(err => {
    console.error('Fatal bot startup error:', err.message);
    process.exit(1);
});
