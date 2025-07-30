#!/bin/bash

# ET-FOOD Git Workflow Script
# Automates committing and pushing all important project changes

set -e  # Exit on any error

echo "🚀 Starting ET-FOOD Git Workflow..."

# Clean up any lock files
if [ -f .git/index.lock ]; then
    rm .git/index.lock
    echo "🧹 Removed Git lock file"
fi

# Clear Python cache
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "🧹 Cleared Python cache"

# Add all files explicitly, ensuring static/uploads is included
git add -A
git add static/uploads/ --force 2>/dev/null || true
git add templates/ --force 2>/dev/null || true
git add *.py --force 2>/dev/null || true
git add *.md --force 2>/dev/null || true
git add requirements.txt --force 2>/dev/null || true

echo "📁 Added all project files to Git"

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "✅ No changes to commit"
    exit 0
fi

# Generate intelligent commit message
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
CHANGED_FILES=$(git diff --cached --name-only | wc -l)
HAS_IMAGES=$(git diff --cached --name-only | grep -q "static/uploads/" && echo "true" || echo "false")
HAS_TEMPLATES=$(git diff --cached --name-only | grep -q "templates/" && echo "true" || echo "false")
HAS_PYTHON=$(git diff --cached --name-only | grep -q "\.py$" && echo "true" || echo "false")

# Build commit message
COMMIT_MSG="Automated sync - $TIMESTAMP"
if [ "$HAS_IMAGES" = "true" ]; then
    COMMIT_MSG="$COMMIT_MSG - Food images updated"
fi
if [ "$HAS_TEMPLATES" = "true" ]; then
    COMMIT_MSG="$COMMIT_MSG - Templates modified"
fi
if [ "$HAS_PYTHON" = "true" ]; then
    COMMIT_MSG="$COMMIT_MSG - Code changes"
fi
COMMIT_MSG="$COMMIT_MSG ($CHANGED_FILES files)"

# Commit changes
git commit -m "$COMMIT_MSG"
echo "✅ Committed changes: $COMMIT_MSG"

# Push to GitHub
git push origin main
echo "🚀 Pushed to GitHub successfully"

# Verify critical files are tracked
echo "📋 Verifying important files are tracked:"
git ls-files static/uploads/ | head -5 | while read file; do
    echo "  ✓ $file"
done

echo "🎉 Git workflow completed successfully!"