# Safe Git Workflow Guide

## Protection Against Data Loss During GitHub Sync

This guide ensures your latest changes and comments are never lost when pulling from GitHub.

## Quick Start

### Before Any Git Pull Operation:

```bash
# 1. Create backup first (recommended)
./pre_pull_backup.sh

# 2. Use safe pull (automatically protects changes)
./safe_git_pull.sh
```

## Scripts Overview

### 🛡️ `safe_git_pull.sh` - Main Protection Script

**What it does:**
- ✅ Automatically detects and saves any unstaged changes
- ✅ Commits staged changes with intelligent messages
- ✅ Pushes local commits before pulling
- ✅ Checks for merge conflicts before proceeding
- ✅ Stops safely if conflicts detected
- ✅ Verifies critical files are preserved after merge
- ✅ Clears Python cache to prevent issues

**Usage:**
```bash
./safe_git_pull.sh
```

### 📦 `pre_pull_backup.sh` - Backup Creation

**What it backs up:**
- 🗂️ `static/uploads/` (all uploaded images)
- 🐍 `app.py`, `models.py`, `routes.py`
- 🎨 `templates/` directory
- 📋 `requirements.txt`, `replit.md`
- 🗄️ Database files (if present)

**Creates:**
- Timestamped backup in `backups/YYYYMMDD_HHMMSS_pre_pull/`
- Automatic restoration script: `restore.sh`

**Usage:**
```bash
./pre_pull_backup.sh
```

## Workflow Examples

### Safe Daily Sync
```bash
# Option A: Full protection (recommended for important changes)
./pre_pull_backup.sh
./safe_git_pull.sh

# Option B: Quick protection (for minor changes)
./safe_git_pull.sh
```

### If Conflicts Are Detected
```bash
# Script will show you:
⚠️  POTENTIAL MERGE CONFLICTS DETECTED!
📋 Files that may conflict:
   app.py
   routes.py

🛑 STOPPING - Please resolve conflicts manually:
   1. Run: git merge origin/main
   2. Resolve any conflicts in the listed files
   3. Run: git add . && git commit
   4. Your work is already safely committed above
```

**Resolution steps:**
1. Your changes are already safely committed
2. Run: `git merge origin/main`
3. Open conflicted files and resolve conflicts
4. Stage resolved files: `git add .`
5. Complete merge: `git commit`

### Emergency Restoration
If something goes wrong after a pull:

```bash
# Find your backup
ls backups/

# Restore from backup
./backups/20250730_143022_pre_pull/restore.sh
```

## File Protection Guarantees

### Always Protected:
- ✅ Your uncommitted changes (auto-committed)
- ✅ Your staged changes (committed before pull)
- ✅ Critical project files (verified after merge)
- ✅ Uploaded images in `static/uploads/`
- ✅ Database changes

### Auto-Commit Messages:
```
Auto-save: Updated app.py - 2025-07-30 14:30:22
Auto-save: Updated 5 files - 2025-07-30 14:30:22
```

## Best Practices

### Before Major Changes:
```bash
# Create backup before significant work
./pre_pull_backup.sh
```

### Daily Workflow:
```bash
# Safe sync at start of day
./safe_git_pull.sh

# Work on your changes...

# Safe sync before ending work
git add .
git commit -m "End of day commit - describe your changes"
git push origin main
```

### Emergency Commands:
```bash
# Check what would be lost (dry run)
git status
git diff

# Manual backup if scripts unavailable
cp -r static/uploads ~/backup_uploads
cp app.py ~/backup_app.py

# Manual safe pull
git add .
git commit -m "Pre-pull safety commit"
git pull origin main
```

## Troubleshooting

### Script Won't Run:
```bash
chmod +x safe_git_pull.sh
chmod +x pre_pull_backup.sh
```

### Still Getting Conflicts:
1. Your changes are safe (already committed)
2. Use Git GUI tools or VS Code for visual conflict resolution
3. Contact for help with complex conflicts

### Files Missing After Pull:
```bash
# Check latest backup
ls -la backups/
./backups/latest_backup/restore.sh
```

## Status Indicators

### ✅ Safe Indicators:
- "Already up to date with GitHub"
- "No conflicts detected - proceeding with safe merge"
- "Safe Git Pull completed successfully!"

### ⚠️ Warning Indicators:
- "POTENTIAL MERGE CONFLICTS DETECTED!"
- "WARNING: Critical files missing after merge"
- "You have X local commits ahead of origin"

### 🛑 Stop Indicators:
- "STOPPING - Please resolve conflicts manually"
- Script exits with conflict detection

---

**Remember: Your work is always protected when using these scripts. They prioritize safety over automation.**