#!/bin/bash

# ET-FOOD Restart Script
# Run after git pull to refresh environment and restore functionality

set -e

echo "🔄 Starting post-pull environment refresh..."

# Clear Python cache to prevent import issues
echo "🧹 Clearing Python cache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Clear any Git lock files
if [ -f .git/index.lock ]; then
    rm .git/index.lock
    echo "🧹 Removed Git lock file"
fi

# Verify critical directories exist
echo "📁 Ensuring critical directories exist..."
mkdir -p static/uploads
mkdir -p templates
mkdir -p static/css
mkdir -p static/js

# Check if database needs initialization
echo "🗄️ Checking database status..."
python3 -c "
import os
from app import app, db
with app.app_context():
    from models import Restaurant, MenuItem, Category
    restaurant_count = Restaurant.query.count()
    if restaurant_count == 0:
        print('Database is empty, initializing...')
        # Import and run the create_tables function
        from app import create_tables
        create_tables()
        print('Database initialized successfully')
    else:
        print(f'Database has {restaurant_count} restaurants - OK')
" || echo "⚠️ Database check failed, but continuing..."

# Restart any background processes if needed
echo "🔄 Process management..."
pkill -f "gunicorn" 2>/dev/null || true
sleep 2

# Verify important files are present
echo "📋 Verifying critical files:"
[ -f "app.py" ] && echo "  ✓ app.py" || echo "  ❌ app.py missing!"
[ -f "models.py" ] && echo "  ✓ models.py" || echo "  ❌ models.py missing!"
[ -f "routes.py" ] && echo "  ✓ routes.py" || echo "  ❌ routes.py missing!"
[ -d "static/uploads" ] && echo "  ✓ static/uploads/" || echo "  ❌ static/uploads/ missing!"
[ -d "templates" ] && echo "  ✓ templates/" || echo "  ❌ templates/ missing!"

# Count uploaded images
IMAGE_COUNT=$(find static/uploads -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -o -name "*.gif" -o -name "*.webp" 2>/dev/null | wc -l)
echo "  📸 Found $IMAGE_COUNT food images"

echo "✅ Environment refresh completed!"
echo "💡 You can now run 'python3 main.py' or restart the Replit workflow"