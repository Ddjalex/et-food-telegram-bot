# ET-FOOD Deployment Guide

## Manual GitHub Push Instructions

Since automatic Git operations are restricted, here's how to manually push to GitHub:

### 1. Download Project Files
Download all project files from Replit or copy them to your local machine.

### 2. Initialize Git Repository Locally
```bash
git init
git config user.name "Ddjalex"
git config user.email "your-email@example.com"
```

### 3. Add Files and Commit
```bash
git add .
git commit -m "Initial commit: ET-FOOD Telegram Bot with Driver Management System

- Complete food delivery system with Telegram bot integration
- Flask web application with admin dashboard
- Driver management with approval/removal system
- Real-time GPS-based driver assignment
- Order workflow from customer to driver delivery
- WebApp interface for menu browsing and ordering
- Enhanced error handling and notification system
- 62 menu items across 14 categories
- Comprehensive driver bot with location tracking
- Payment system with transaction management
- Live location sharing and order tracking"
```

### 4. Add Remote Repository
```bash
git remote add origin https://github.com/Ddjalex/et-food-telegram-bot.git
git branch -M main
```

### 5. Push to GitHub with Personal Access Token
```bash
git push -u origin main
```

When prompted for credentials:
- **Username**: `Ddjalex`
- **Password**: Use your `GITHUB_PERSONAL_ACCESS_TOKEN`

## Alternative: Using GitHub CLI

If you have GitHub CLI installed:
```bash
gh auth login --with-token < your_token_file
gh repo create et-food-telegram-bot --public
git remote add origin https://github.com/Ddjalex/et-food-telegram-bot.git
git push -u origin main
```

## Environment Variables for Production

Create a `.env` file or set these environment variables:

```env
BOT_TOKEN=your_telegram_bot_token
DRIVER_BOT_TOKEN=your_driver_bot_token
SESSION_SECRET=your_session_secret_key
ADMIN_PASSWORD=your_admin_password
DATABASE_URL=sqlite:///food_delivery.db
WEBHOOK_URL=https://your-domain.com
```

## Deployment Options

### 1. Replit Deployment
- Import project to Replit
- Set environment secrets in Replit
- Run with: `gunicorn --bind 0.0.0.0:5000 main:app`

### 2. Heroku Deployment
```bash
heroku create et-food-telegram-bot
heroku config:set BOT_TOKEN=your_token
heroku config:set DRIVER_BOT_TOKEN=your_driver_token
heroku config:set SESSION_SECRET=your_secret
heroku config:set ADMIN_PASSWORD=your_password
git push heroku main
```

### 3. VPS Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BOT_TOKEN=your_token
export DRIVER_BOT_TOKEN=your_driver_token
export SESSION_SECRET=your_secret
export ADMIN_PASSWORD=your_password

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
```

### 4. Docker Deployment
```bash
# Build image
docker build -t et-food-bot .

# Run container
docker run -p 5000:5000 \
  -e BOT_TOKEN=your_token \
  -e DRIVER_BOT_TOKEN=your_driver_token \
  -e SESSION_SECRET=your_secret \
  -e ADMIN_PASSWORD=your_password \
  et-food-bot
```

## Post-Deployment Setup

### 1. Set Telegram Webhooks
The application automatically sets webhooks when it starts. Ensure your deployment URL is accessible via HTTPS.

### 2. Create Admin User
Access `/admin` and use your `ADMIN_PASSWORD` to log in.

### 3. Set Up Initial Menu
The system includes 62 pre-configured menu items. You can modify them through the admin dashboard.

### 4. Add Drivers
Use the admin dashboard to add and approve drivers. Drivers need to start the driver bot and share their contact.

## Security Considerations

1. **Use HTTPS** for webhook endpoints
2. **Secure environment variables** - never commit tokens to Git
3. **Regular token rotation** for bot tokens
4. **Database backups** for production deployments
5. **Monitor logs** for suspicious activity

## Troubleshooting

### Common Issues
1. **Bot not responding**: Check BOT_TOKEN and webhook URL
2. **Driver notifications failing**: Ensure DRIVER_BOT_TOKEN is correct
3. **Database errors**: Check DATABASE_URL and permissions
4. **Webhook errors**: Verify HTTPS and certificate validity

### Logs
Check application logs for detailed error messages:
```bash
tail -f /var/log/et-food-bot.log
```

## Monitoring

Set up monitoring for:
- Bot response times
- Order processing rates
- Driver assignment success
- Database performance
- Error rates

## Backup Strategy

1. **Database backups**: Regular SQLite/PostgreSQL backups
2. **Code backups**: Git repository
3. **Configuration backups**: Environment variables documentation
4. **Media backups**: Uploaded images and documents

## Support

For deployment issues:
1. Check the logs first
2. Verify environment variables
3. Test bot tokens separately
4. Review webhook configuration
5. Contact development team if needed

## System Requirements

- **Python**: 3.8+
- **Memory**: 512MB minimum, 1GB recommended
- **Storage**: 1GB for database and uploads
- **Network**: HTTPS endpoint for webhooks
- **OS**: Linux/Unix recommended

## Performance Optimization

1. **Database indexing**: For order and driver queries
2. **Caching**: Redis for session storage
3. **Load balancing**: Multiple worker processes
4. **CDN**: For static assets
5. **Monitoring**: Application performance monitoring

This guide ensures successful deployment of the ET-FOOD system to your GitHub repository and production environment.