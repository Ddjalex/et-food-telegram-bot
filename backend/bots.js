require('dotenv').config({ path: require('path').join(__dirname, '../.env.example') });

console.log('Starting ET-FOOD Telegram Bots...');

require('./customer_bot');
require('./driver_bot');

console.log('Both bots are running!');
