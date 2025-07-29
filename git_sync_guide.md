# Git Synchronization Guide for ET-FOOD Project

## Current Issues Identified
1. Git lock files preventing operations (.git/index.lock, .git/objects/maintenance.lock)
2. 2,370 cached Python files (__pycache__, *.pyc) that can cause conflicts
3. Database files (*.db, *.sqlite) being ignored but local changes persisting
4. Replit environment caching that doesn't refresh after pull

## Step-by-Step Solution

### 1. Clean Up Before Committing
```bash
# Remove all cached Python files
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Remove Git lock files (if they exist)
rm -f .git/index.lock
rm -f .git/objects/maintenance.lock

# Check what files are actually tracked
git ls-files | head -20
```

### 2. Proper Commit Process
```bash
# Check current status
git status

# Add all important files (this will respect .gitignore)
git add .

# Commit with meaningful message
git commit -m "Migration completed: Fixed Flask app structure, PostgreSQL integration, and database initialization"

# Push to GitHub
git push origin main
```

### 3. Verify Upload Success
Before pulling in Replit, verify on GitHub web interface:
- Check that your latest commit appears
- Verify static/uploads folder and images are present
- Confirm all Python files show your latest changes

### 4. Proper Pull Process in Replit
```bash
# Fetch latest from GitHub
git fetch origin main

# Show what will change
git diff HEAD origin/main --name-only

# Hard reset to match GitHub exactly
git reset --hard origin/main

# Clean any untracked files
git clean -fd
```

### 5. Force Replit Environment Refresh
After pulling:
1. Stop the current workflow (if running)
2. Clear browser cache (Ctrl+Shift+R)
3. Restart the workflow
4. Wait for application to fully initialize

## Files Currently Tracked in Git
- All .py files (your application code)
- static/uploads/ directory with food images (76 images tracked)
- Configuration files (requirements.txt, etc.)
- Templates and CSS files

## Important Notes
- Your .gitignore is correctly configured
- static/uploads IS being tracked (comments show it's intentionally included)
- Database files are properly ignored
- The 76 files in static/uploads should persist after pull

## Troubleshooting
If files still revert:
1. Check if you're on the correct branch: `git branch`
2. Verify GitHub shows your changes online
3. Try a fresh Replit import from GitHub
4. Check if any files are locked by Replit processes

## Prevention
- Always commit before major changes
- Use meaningful commit messages
- Verify pushes on GitHub web interface
- Clear Python cache regularly
- Don't edit files during active workflows