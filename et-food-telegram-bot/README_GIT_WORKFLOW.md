# ET-FOOD Git Workflow System

Complete automation system for managing Git operations in Replit environment to ensure all files persist correctly.

## 🚀 Quick Start

### Daily Workflow Commands
```bash
# Complete workflow: clean, commit, push
./git_workflow.sh full

# Just commit changes
./git_workflow.sh commit

# Pull and restart environment
./git_workflow.sh pull && ./restart_after_pull.sh
```

### First Time Setup
```bash
# Set up Git hooks for automated checks
./git_hooks_setup.sh

# Verify all important files are tracked
./git_workflow.sh verify
```

## 📁 What Gets Committed

### ✅ Always Tracked
- **Python Files**: All .py files (app.py, models.py, routes.py, etc.)
- **Static Assets**: All files in static/uploads/ (food images, logos)
- **Templates**: HTML templates and CSS files
- **Configuration**: requirements.txt, .gitignore, workflow scripts
- **Documentation**: README files, guides, changelog

### ❌ Always Ignored
- **Cache Files**: __pycache__/, *.pyc
- **Database Files**: *.db, *.sqlite, *.sqlite3
- **Environment**: .env, .venv/, instance/
- **System Files**: .DS_Store, Thumbs.db
- **Replit Config**: .replit, .upm/, .cache/

## 🔧 Available Scripts

### 1. `git_workflow.sh` - Main Git Operations
```bash
./git_workflow.sh cleanup   # Clean locks and cache
./git_workflow.sh verify    # Check file tracking
./git_workflow.sh commit    # Clean + commit
./git_workflow.sh push      # Clean + commit + push
./git_workflow.sh pull      # Pull latest changes
./git_workflow.sh full      # Complete workflow
```

### 2. `restart_after_pull.sh` - Environment Refresh
```bash
./restart_after_pull.sh full     # Complete restart
./restart_after_pull.sh stop     # Stop processes only
./restart_after_pull.sh clear    # Clear cache only
./restart_after_pull.sh verify   # Check file integrity
./restart_after_pull.sh status   # Show environment status
```

### 3. `git_hooks_setup.sh` - Install Git Hooks
- **Pre-commit**: Checks Python syntax and file sizes
- **Post-commit**: Shows commit summary

## 🔄 Complete Workflow Process

### For Making Changes
1. Make your code/file changes
2. Run: `./git_workflow.sh full`
3. Verify on GitHub that changes appear
4. Continue development

### For Pulling Updates
1. Run: `./git_workflow.sh pull`
2. Run: `./restart_after_pull.sh full`
3. Restart the "Start application" workflow in Replit
4. Verify all files and images loaded correctly

### For Emergency Recovery
If files are missing or reverted:
```bash
# Force reset to GitHub state
git fetch origin main
git reset --hard origin/main
./restart_after_pull.sh full
```

## 📊 File Status Monitoring

The scripts automatically track:
- **74+ food images** in static/uploads/
- **40+ Python files** across the project
- **HTML templates** and CSS files
- **Configuration files**

## 🔍 Troubleshooting

### Git Lock Files
```bash
./git_workflow.sh cleanup
```

### Missing Files After Pull
```bash
./git_workflow.sh verify
./restart_after_pull.sh verify
```

### Environment Not Refreshing
```bash
./restart_after_pull.sh full
# Then restart the Replit workflow
```

## 🛡️ Safety Features

### Pre-commit Checks
- Python syntax validation
- Large file detection (>10MB warning)
- Important file verification

### Auto-generated Commit Messages
- Includes timestamp
- Describes types of changes (code, images, templates)
- Meaningful commit history

### File Integrity Verification
- Checks for critical files (app.py, main.py, models.py)
- Counts tracked images and templates
- Alerts for missing important files

## 🔗 Integration with Replit

### Environment Variables
Scripts work with existing Replit configuration:
- Respects DATABASE_URL for PostgreSQL
- Preserves bot tokens and secrets
- Maintains workflow configurations

### Workflow Restart
After pulling changes:
1. Scripts prepare the environment
2. Manual restart of "Start application" workflow required
3. Automatic verification of file integrity

## 📝 Best Practices

1. **Always use the scripts** instead of manual git commands
2. **Verify on GitHub** after pushing changes
3. **Restart workflow** after pulling updates
4. **Check file counts** to ensure all assets are tracked
5. **Use meaningful branch names** for different features

This system ensures your ET-FOOD project files never get lost and the environment stays properly synchronized with GitHub.