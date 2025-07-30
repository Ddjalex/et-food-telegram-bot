#!/bin/bash

# Pre-Pull Backup Script - Creates backup before any Git operations
# Usage: ./pre_pull_backup.sh

set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)_pre_pull"
echo "🔄 Creating pre-pull backup..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup critical files and directories
echo "📦 Backing up critical files to: $BACKUP_DIR"

# Copy important files
cp -r static/uploads "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  static/uploads not found"
cp app.py "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  app.py not found"
cp models.py "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  models.py not found"
cp routes.py "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  routes.py not found"
cp -r templates "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  templates not found"
cp requirements.txt "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  requirements.txt not found"
cp replit.md "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  replit.md not found"

# Backup database if it exists
cp instance/food_delivery.db "$BACKUP_DIR/" 2>/dev/null || echo "ℹ️  No SQLite database to backup"

# Create restoration script
cat > "$BACKUP_DIR/restore.sh" << 'EOF'
#!/bin/bash
echo "🔄 Restoring from backup..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

# Restore files
cp -r "$SCRIPT_DIR/uploads" static/ 2>/dev/null || true
cp "$SCRIPT_DIR/app.py" . 2>/dev/null || true
cp "$SCRIPT_DIR/models.py" . 2>/dev/null || true
cp "$SCRIPT_DIR/routes.py" . 2>/dev/null || true
cp -r "$SCRIPT_DIR/templates" . 2>/dev/null || true
cp "$SCRIPT_DIR/requirements.txt" . 2>/dev/null || true
cp "$SCRIPT_DIR/replit.md" . 2>/dev/null || true
cp "$SCRIPT_DIR/food_delivery.db" instance/ 2>/dev/null || true

echo "✅ Backup restored successfully"
EOF

chmod +x "$BACKUP_DIR/restore.sh"

echo "✅ Backup created successfully!"
echo "📁 Location: $BACKUP_DIR"
echo "🔄 To restore: ./$BACKUP_DIR/restore.sh"