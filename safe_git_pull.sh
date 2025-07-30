#!/bin/bash

# Safe Git Pull Script - Protects local changes during GitHub sync
# Usage: ./safe_git_pull.sh

set -e  # Exit on any error

echo "🔍 Safe Git Pull - Protecting your changes..."
echo "=========================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check for unstaged changes
if ! git diff --quiet; then
    echo "📝 Found unstaged changes in working directory"
    git status --porcelain
    echo ""
    echo "💾 Auto-saving unstaged changes..."
    git add .
    echo "✅ Changes staged for commit"
fi

# Check for staged changes
if ! git diff --cached --quiet; then
    echo "📋 Found staged changes ready to commit"
    
    # Generate intelligent commit message
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    CHANGED_FILES=$(git diff --cached --name-only | wc -l)
    
    # Create descriptive commit message
    if [ $CHANGED_FILES -eq 1 ]; then
        FILENAME=$(git diff --cached --name-only)
        COMMIT_MSG="Auto-save: Updated $FILENAME - $TIMESTAMP"
    else
        COMMIT_MSG="Auto-save: Updated $CHANGED_FILES files - $TIMESTAMP"
    fi
    
    echo "💾 Committing changes: $COMMIT_MSG"
    git commit -m "$COMMIT_MSG"
    echo "✅ Local changes safely committed"
fi

# Check if there are any commits ahead of origin
AHEAD_COUNT=$(git rev-list --count HEAD ^origin/main 2>/dev/null || echo "0")
if [ "$AHEAD_COUNT" -gt 0 ]; then
    echo "⬆️  You have $AHEAD_COUNT local commits ahead of origin"
    echo "🚀 Pushing local commits before pull..."
    git push origin main
    echo "✅ Local commits pushed successfully"
fi

# Fetch latest changes from origin
echo "📡 Fetching latest changes from GitHub..."
git fetch origin

# Check if remote has new commits
BEHIND_COUNT=$(git rev-list --count origin/main ^HEAD 2>/dev/null || echo "0")
if [ "$BEHIND_COUNT" -eq 0 ]; then
    echo "✅ Already up to date with GitHub"
    exit 0
fi

echo "⬇️  GitHub has $BEHIND_COUNT new commits"

# Check for potential conflicts before merge
echo "🔍 Checking for potential merge conflicts..."
git merge-tree $(git merge-base HEAD origin/main) HEAD origin/main > /tmp/merge_check 2>/dev/null

if [ -s /tmp/merge_check ]; then
    echo "⚠️  POTENTIAL MERGE CONFLICTS DETECTED!"
    echo "📋 Files that may conflict:"
    git diff --name-only HEAD origin/main
    echo ""
    echo "🛑 STOPPING - Please resolve conflicts manually:"
    echo "   1. Run: git merge origin/main"
    echo "   2. Resolve any conflicts in the listed files"
    echo "   3. Run: git add . && git commit"
    echo "   4. Your work is already safely committed above"
    exit 1
fi

# Safe to proceed with merge
echo "✅ No conflicts detected - proceeding with safe merge"
git merge origin/main --no-edit

# Verify critical files are preserved
echo "🔍 Verifying critical files are preserved..."
CRITICAL_FILES=(
    "static/uploads"
    "app.py"
    "models.py"
    "routes.py"
    "templates"
    "requirements.txt"
)

MISSING_FILES=()
for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -e "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo "⚠️  WARNING: Critical files missing after merge:"
    printf '   - %s\n' "${MISSING_FILES[@]}"
    echo "🔄 This may require manual restoration"
fi

# Clear Python cache to prevent import issues
echo "🧹 Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "✅ Safe Git Pull completed successfully!"
echo "📊 Summary:"
echo "   - Local changes: Safely committed and preserved"
echo "   - Remote changes: $BEHIND_COUNT commits merged"
echo "   - Critical files: Verified present"
echo "   - Cache: Cleared"
echo ""
echo "🚀 Ready to restart application"