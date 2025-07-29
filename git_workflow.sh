#!/bin/bash
# Git Workflow Automation for ET-FOOD Project
# This script ensures all important files are committed and pushed properly

set -e

echo "🚀 Starting Git Workflow for ET-FOOD Project..."

# Function to clean up Git locks and cache
cleanup_git() {
    echo "🧹 Cleaning up Git locks and Python cache..."
    
    # Remove Git lock files if they exist
    rm -f .git/index.lock 2>/dev/null || true
    rm -f .git/objects/maintenance.lock 2>/dev/null || true
    rm -f .git/refs/heads/*.lock 2>/dev/null || true
    
    # Clean Python cache files
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # Clean temporary files
    find . -name "*.tmp" -delete 2>/dev/null || true
    find . -name "*.temp" -delete 2>/dev/null || true
    
    echo "✅ Cleanup completed"
}

# Function to verify important files are tracked
verify_tracking() {
    echo "🔍 Verifying important files are tracked..."
    
    # Check static/uploads directory
    upload_count=$(git ls-files static/uploads/ | wc -l)
    echo "📁 Static uploads tracked: $upload_count files"
    
    # Check Python files
    py_count=$(git ls-files "*.py" | wc -l)
    echo "🐍 Python files tracked: $py_count files"
    
    # Check templates
    template_count=$(git ls-files templates/ 2>/dev/null | wc -l || echo "0")
    echo "📄 Template files tracked: $template_count files"
    
    # Check if any important files are untracked
    untracked_important=$(git status --porcelain | grep "^??" | grep -E "\.(py|html|css|js|jpg|jpeg|png|gif)$" | wc -l)
    if [ "$untracked_important" -gt 0 ]; then
        echo "⚠️  Found $untracked_important untracked important files:"
        git status --porcelain | grep "^??" | grep -E "\.(py|html|css|js|jpg|jpeg|png|gif)$"
    fi
}

# Function to commit all changes
commit_changes() {
    echo "💾 Committing changes..."
    
    # Add all files (respects .gitignore)
    git add .
    
    # Check if there are changes to commit
    if git diff --staged --quiet; then
        echo "ℹ️  No changes to commit"
        return 0
    fi
    
    # Show what will be committed
    echo "📋 Files to be committed:"
    git diff --staged --name-only | head -20
    
    # Create commit message based on changes
    COMMIT_MSG="Auto-commit: $(date '+%Y-%m-%d %H:%M:%S') - "
    
    # Check types of changes
    if git diff --staged --name-only | grep -q "\.py$"; then
        COMMIT_MSG="${COMMIT_MSG}Code updates, "
    fi
    if git diff --staged --name-only | grep -q "static/uploads/"; then
        COMMIT_MSG="${COMMIT_MSG}Image assets, "
    fi
    if git diff --staged --name-only | grep -q "templates/"; then
        COMMIT_MSG="${COMMIT_MSG}Template updates, "
    fi
    
    # Remove trailing comma and space
    COMMIT_MSG=$(echo "$COMMIT_MSG" | sed 's/, $//')
    
    # Commit with generated message
    git commit -m "$COMMIT_MSG"
    echo "✅ Changes committed: $COMMIT_MSG"
}

# Function to push to GitHub
push_changes() {
    echo "📤 Pushing to GitHub..."
    
    # Get current branch
    BRANCH=$(git branch --show-current)
    echo "📍 Current branch: $BRANCH"
    
    # Push changes
    if git push origin "$BRANCH"; then
        echo "✅ Successfully pushed to GitHub"
        
        # Show latest commit
        echo "📝 Latest commit:"
        git log --oneline -1
    else
        echo "❌ Failed to push to GitHub"
        return 1
    fi
}

# Function to pull and refresh environment
pull_and_refresh() {
    echo "⬇️  Pulling latest changes from GitHub..."
    
    # Fetch latest changes
    git fetch origin
    
    # Get current branch
    BRANCH=$(git branch --show-current)
    
    # Show what will change
    echo "📋 Changes to pull:"
    git diff HEAD origin/"$BRANCH" --name-only | head -10
    
    # Pull changes
    git pull origin "$BRANCH"
    
    echo "🔄 Refreshing Replit environment..."
    # This will be handled by the restart script
    echo "✅ Pull completed - restart workflow to refresh environment"
}

# Main workflow
main() {
    case "${1:-commit}" in
        "cleanup")
            cleanup_git
            ;;
        "verify")
            verify_tracking
            ;;
        "commit")
            cleanup_git
            verify_tracking
            commit_changes
            ;;
        "push")
            cleanup_git
            verify_tracking
            commit_changes
            push_changes
            ;;
        "pull")
            cleanup_git
            pull_and_refresh
            ;;
        "full")
            cleanup_git
            verify_tracking
            commit_changes
            push_changes
            ;;
        *)
            echo "Usage: $0 [cleanup|verify|commit|push|pull|full]"
            echo ""
            echo "Commands:"
            echo "  cleanup  - Clean Git locks and cache files"
            echo "  verify   - Check that important files are tracked"
            echo "  commit   - Clean, verify, and commit changes"
            echo "  push     - Clean, verify, commit, and push"
            echo "  pull     - Clean and pull latest changes"
            echo "  full     - Complete workflow: clean, verify, commit, push"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"