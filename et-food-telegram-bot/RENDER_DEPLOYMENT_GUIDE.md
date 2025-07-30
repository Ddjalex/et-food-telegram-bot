# Render Deployment Guide - ET-FOOD Bot System

## Environment Variables Required on Render

To make your ET-FOOD bot system work on Render, you need to configure these environment variables in your Render dashboard:

### Required Bot Tokens
1. **ETFASTFOOD_BOT_TOKEN** - Your customer food ordering bot token
   - Get this from @BotFather on Telegram
   - Example format: `7956456272:AAG3yedWGwhjdoIUIwZaQDuBuuTL9vbp7hw`

2. **DRIVER_BOT_TOKEN** - Your delivery driver bot token  
   - Get this from @BotFather on Telegram
   - Example format: `7679369276:AAEzDjI5ODw7KR7qVyBsT_3STyz0bTqJ6is`

### Required for Webhook Configuration
3. **RENDER_EXTERNAL_URL** - Your Render app URL
   - Set this to your app's URL: `https://et-food-telegram-bot.onrender.com`
   - This is used for webhook registration with Telegram

### Optional Environment Variables
- **ADMIN_PASSWORD** - Admin panel password (default: admin123)
- **SESSION_SECRET** - Flask session secret key
- **DATABASE_URL** - Database connection string (uses SQLite by default)

## How to Set Environment Variables on Render

1. Go to your Render dashboard
2. Select your web service
3. Click on "Environment" tab
4. Add each environment variable:
   - Key: `ETFASTFOOD_BOT_TOKEN`
   - Value: Your actual bot token from @BotFather
   - Click "Add"
   - Repeat for `DRIVER_BOT_TOKEN` and `RENDER_EXTERNAL_URL`

## Webhook Endpoints

Your deployment will automatically register these webhooks:
- Customer bot: `https://your-app.onrender.com/webhook`
- Driver bot: `https://your-app.onrender.com/driver-webhook`

## Testing the Deployment

After setting the environment variables:
1. Wait for Render to redeploy your app (should happen automatically)
2. Check the deployment logs for successful webhook registration
3. Test your bots by sending `/start` commands
4. Verify both customer and driver bots respond properly

## Common Issues

**Driver bot not responding**: 
- Check that DRIVER_BOT_TOKEN is set correctly
- Verify RENDER_EXTERNAL_URL is your actual app URL
- Check deployment logs for webhook registration success

**Customer bot not responding**:
- Check that ETFASTFOOD_BOT_TOKEN is set correctly
- Verify webhook endpoint is accessible

## Production Checklist

- [ ] ETFASTFOOD_BOT_TOKEN configured
- [ ] DRIVER_BOT_TOKEN configured  
- [ ] RENDER_EXTERNAL_URL set to your app URL
- [ ] Both bots responding to /start commands
- [ ] Webhook registration successful in logs
- [ ] WebApp interface loading properly
- [ ] Admin dashboard accessible